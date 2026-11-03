# F136: повторный допуск требований перед исправлением старого callback

Дата: 2026-10-18. Независимый reviewer: `review_f290_infra`.
Ветка: `codex/136-auth-navigation-recovery`.
База: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Режим: **high-risk-product**, авторизация, границы сеанса и навигация macOS.

## Решение

**PASS допуска требований: 35 checked / 0 unchecked.** Каждый пункт повторно
проверен по прочитанным текущим документам. Можно исправлять подтверждённый
P2 в пределах существующего среза T005/T006/T010/T017 после остальных
обязательных ворот анализа и учёта задач, которые основной исполнитель
подтверждает отдельно. Новый продуктовый вопрос или изменение конституции
для этого исправления не требуется.

**Request Changes к реализации сохраняется.** Этот отчёт не принимает код,
не закрывает находку и не заменяет итоговое независимое ревью. До исправления
остаётся доказанный сбой из `review-session-boundary-20261018.md`.

## Повторно прочитанные источники и границы

Прочитаны оба checklist, spec, plan, tasks, quickstart, research, data-model,
contract и прежние индивидуальные основания R01–R16/CHK001–CHK019.
AGENTS, guidance README, codex-worktrees, spec-kit-flow, product-gates и
конституция 7.1.0 прочитаны полностью; release-and-validation — относящиеся к
этому этапу строки 1–175 (локальная диагностика и точные проверки PR).
Продуктовая граница повторно сверена с PRD §4.x–4.y и текущим статусом F013/F047:
сервер владеет авторизацией, готовность кабинета требует безопасной
авторизованной страницы, native Record/Stop остаётся независимым.

Фактическая ветка, `.specify/feature.json`, spec/tasks и результат
`check-prerequisites.sh --json --paths-only` согласованы по F136. Канонический
BRANCH `136-auth-navigation-recovery` в результате скрипта не подменяет
фактическую ветку `codex/136-auth-navigation-recovery`.
Новых checklist или продуктовых требований reviewer не создавал.

## Ключевые условия исправления

| Условие | Текущее основание | Вывод |
|---|---|---|
| Старые callbacks | Spec «Текущая приёмка»: отложенные/устаревшие callbacks не применяют границу к новому переходу; plan resumed §4–5 требует все callers и сохранение navigation identity; data-model/contract повторяют запрет | Требование полное. Поздние redirect/finish и redirect/failure должны проверяться в реализации; старый redirect не вправе завершать новую принятую форму до её start. |
| POST → 303 → GET | US3.1 требует единственное действие и финальную безопасную страницу; FR001/003/006/007 и SC002 запрещают повтор; research «Подтверждать перенаправление по идентичности» задаёт доказанную причину 303 | Полнота достаточна. Законный серверный GET после 303 допустим; запрещён именно новый GET, искусственно воспроизводящий исходное действие через SwiftUI. Исправление stale callback обязано сохранить актуальную redirect chain. |
| Ошибка обычной формы | Clarifications, FR006 и текущая приёмка: ошибка POST не меняет сессию и не пересоздаёт кабинет; FR008 — безопасный ручной повтор | Полнота достаточна. Нет разрешения автоматически повторять POST или оставлять бесконечную загрузку. |
| Отмена | Те же FR006/008 и quickstart явно включают cancel, сохранение WebView и единственный POST | Полнота достаточна. Безопасное завершение состояния не тождественно успешному ответу сервера. |
| 401 / выбор пространства | FR004, plan resumed §3, data-model/contract: немедленный запрет защищённой истории; успешная граница после route/request commit | Нет противоречия с отложенным успешным переходом. Защита не ждёт успешной загрузки следующей страницы. |

В spec/research сохранено исходное наблюдение о неизвестной причине 303.
Это историческое условное ограничение: «пока причинная связь не доказана».
Позднейший раздел research явно фиксирует такую причинную проверку и запрещает
ослаблять identity ради обхода. Требования не утверждают, что любая старая
redirect identity становится актуальной. Допуск не подтверждает выбранный
ошибочный алгоритм, а разрешает его исправление в тех же поведенческих границах.
Основному исполнителю нужно отразить актуальный вывод в convergence/validation;
reviewer spec/plan/tasks не меняет.

## Повторная проверка всех пунктов качества spec

R01–R16 — порядок пунктов `requirements.md` сверху вниз.

| Пункт | Решение | Повторно найденное основание |
|---|---|---|
| R01 | checked | Spec задаёт наблюдаемое поведение; алгоритм WebKit находится в plan/research. |
| R02 | checked | US1–3 связывают вход, навигацию и формы с предотвращением белого экрана/повторного действия. |
| R03 | checked | Русские пользовательские сценарии и результаты понятны без чтения классов кода. |
| R04 | checked | Сценарии, требования, сущности и измеримые критерии присутствуют. |
| R05 | checked | Неразрешённых NEEDS CLARIFICATION нет; session 2026-10-17 ограничивает текущий срез. |
| R06 | checked | FR001–009 и текущая приёмка задают проверяемые запреты и порядок событий. |
| R07 | checked | SC001 ≤10s; SC002 один action; SC003/004 проверяемые результаты истории и кнопок. |
| R08 | checked | SC оценивают поведение независимо от SwiftUI/WKWebView механизма. |
| R09 | checked | Каждый US имеет independent test/acceptance; текущая приёмка добавляет error/cancel/stale. |
| R10 | checked | Edge Cases покрывают cancel/restart/server error/rate limit/session expiry/query и normal pages. |
| R11 | checked | Assumptions и Clarifications исключают изменение server auth/storage/access и отделяют OAuth/manual. |
| R12 | checked | Существующие маршруты, synthetic automation и разрешённый тестовый аккаунт для T016 определены. |
| R13 | checked | FR001/007→SC002, FR002–005→US2/SC003, FR006→SC004, FR008→US1/edge, FR009→T010. |
| R14 | checked | Email/VK/Яндекс, native controls, настройки/provider link охвачены; незавершённое не скрыто. |
| R15 | checked | SC001–004 позволяют измерить результат; отметка не означает уже полученный PASS реализации. |
| R16 | checked | Spec не предписывает классы/поля или конкретный способ смены SwiftUI identity. |

## Повторная проверка auth-navigation

| Пункт | Решение | Повторно найденное основание |
|---|---|---|
| CHK001 | checked | Key Entities/FR002–003/data-model различают stable GET и transient action. |
| CHK002 | checked | US1/US3 и continuation table разделяют primary sign-in и authenticated provider link. |
| CHK003 | checked | FR004 и session table охватывают login/logout/expiry/reselection. |
| CHK004 | checked | Assumptions/FR007/contract Boundary исключают server methods/providers/storage. |
| CHK005 | checked | FR001/003/007 и SC002 запрещают replay и подмену исходного метода. |
| CHK006 | checked | FR002–005/US2/contract invariant3 задают общую политику кнопок, жестов и восстановления. |
| CHK007 | checked | FR004/current acceptance требуют stable route до успешной границы и немедленный запрет при401. |
| CHK008 | checked | FR006/US2.2 сохраняют normal history; FR003–005 исключают transient/prior-session. |
| CHK009 | checked | US1/SC001–002 и T016 перечисляют способы входа, однократность и безопасную ошибку. |
| CHK010 | checked | US2/FR005–006/SC003–004/Observable behavior различают transient и normal controls. |
| CHK011 | checked | Edge Cases/FR008/quickstart включают cancel, server error, rate limit, restart и ручной retry. |
| CHK012 | checked | FR007/quickstart исключают secrets/codes/cookies/content из evidence и диагностики. |
| CHK013 | checked | FR009/plan/T010 сохраняют accessible names и согласованность состояния controls. |
| CHK014 | checked | FR007/contract Boundary/research сохраняют существующие server routes и запрещают GET workaround. |
| CHK015 | checked | Assumptions/quickstart/T016 ограничивают automation синтетикой, manual — GRAF Dev/разрешённым аккаунтом. |
| CHK016 | checked | Clarifications/plan resumed/tasks restoration разделяют текущий срез и открытые OAuth/manual задачи. |
| CHK017 | checked | FR001/006/current acceptance/quickstart требуют сохранения сессии при200/error/cancel без replay. |
| CHK018 | checked | FR004/current acceptance/data-model/contract явно задают successful ordering, immediate401 и stale exclusion. |
| CHK019 | checked | Research разделяет исходный RED, последующую причину303 и текущие проверки; T016 не заменён автотестами. |

## Неподтверждённые этапы

T005/T006/T010/T017 остаются незавершёнными до исправления P2 и новой проверки.
T004/#4731, T011/#4738, T012/#4739 и T016/#4743 остаются отдельными открытыми
этапами OAuth/ручной приёмки. Долг root-only auth paths не считается устранённым;
исторические `[X]` не подтверждают текущее выполнение. Допуск не разрешает
коммит, merge, release или deploy и не свидетельствует о прохождении CI.
Reviewer не менял код/spec/plan/tasks, не запускал тесты или приложение,
не обращался к GitHub и не затрагивал чужие изменения.

## Повторное чтение и итог

После добавления reviewer notes оба checklist перечитаны целиком и пересчитаны:

| Checklist | Checked | Unchecked |
|---|---:|---:|
| requirements.md | 16 | 0 |
| auth-navigation.md | 19 | 0 |
| Всего | 35 | 0 |

Отметки не изменены: все основания подтверждены повторно. Прежнее итоговое
ревью кода с Request Changes действует до отдельной перепроверки исправления.

## Контрольные суммы текущих прочитанных документов

Следующие хеши фиксируют документы этого допуска. Это новый снимок после
полного чтения, а не утверждение о сравнении с неизвестными прежними хешами.
У release guidance/PRD/status прочитаны области, указанные выше.

| Файл | SHA256 |
|---|---|
| AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| .specify/feature.json | `368b377c6182cd4f89813cf030b207a0ff8f2fef65c9e38ab2887905859c9c38` |
| .specify/memory/constitution.md | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| docs/agent-guidance/README.md | `40e357e422c60915d2c4334c83b9ab74f5ef4c0df6ab8831e3ed16e281ba18a6` |
| docs/agent-guidance/codex-worktrees.md | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| docs/agent-guidance/spec-kit-flow.md | `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887` |
| docs/agent-guidance/product-gates.md | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| docs/agent-guidance/release-and-validation.md | `e3d24689a330634ec5ef87d829f8bcbf16bb7b81e0196b9d0baae4f49f27278d` |
| docs/prd-voice-layer-final.md | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| docs/current-product-status.md | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| specs/136-auth-navigation-recovery/spec.md | `04b155b65ba5760748c19a7c92a7e527e7ada781a22b44b0817aec6473e8c4fc` |
| specs/136-auth-navigation-recovery/plan.md | `89e2d8a84239cae183f77593280fbe73436d881e980138523a1753b1093aafc3` |
| specs/136-auth-navigation-recovery/tasks.md | `8d1ac06ab52c5b2d5eb0a25ae33ed44c8f3e0075bae5b449433b97e756078d36` |
| specs/136-auth-navigation-recovery/quickstart.md | `3d3be9800e385c3e90e7b5568c022636bb41668c80e103818f09acdcc80bf5a1` |
| specs/136-auth-navigation-recovery/research.md | `5494a84d795102bf03f616b12d6f1dbe8acc905a5f5214a53ddb87fbef87c6b2` |
| specs/136-auth-navigation-recovery/data-model.md | `ea2683c1e7838b9d154508fac52f37e2b9f5098b4a443f3f793e164c257136ac` |
| specs/136-auth-navigation-recovery/contracts/cabinet-navigation-lifecycle.md | `fd3a209a57af6057c618d8667b64e62c97bf485db958d69f2665518a4929726f` |
