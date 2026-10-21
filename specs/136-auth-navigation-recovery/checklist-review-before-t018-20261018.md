# F136: независимый допуск требований перед T018

Дата: 2026-10-18. Reviewer: `review_f290_infra`.
Фактическая ветка: `codex/136-auth-navigation-recovery`.
База: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Режим: **high-risk-product**, существующий Spec Kit срез с convergence.

## Решение

**PASS требований перед T018: 36 checked / 0 unchecked.**
T018 разрешена требованиями существующей F136; продуктовые неоднозначности,
противоречия с конституцией и недостающие критерии допуска не найдены.
Основной исполнитель отдельно завершает обязательную синхронизацию новой
задачи с GitHub до кода; этот reviewer GitHub не меняет и sync PASS не заявляет.

Это допуск к реализации в рамках требований, а не PASS реализации T018.
Требуются RED/GREEN, итоговое независимое ревью, convergence и текущие проверки.
Разрешение коммита/merge/release/deploy этим отчётом не предоставляется.

## Процедура повторной проверки

Оба reviewer checklist перечитаны полностью. Для ранее полностью прочитанных
неизменных документов применена проверяемая процедура:

1. Взята таблица SHA256 из собственного
   `checklist-recheck-before-stale-fix-20261018.md`, созданная после полного
   чтения spec/plan/constitution/guidance и supporting documents.
2. Каждый текущий файл заново прочитан для вычисления SHA256. Сравнены все
   17 записей таблицы: 16 совпали; единственное отличие — tasks.md с новой T018.
   Конкретные совпадения приведены ниже, не восстановлены из предположений.
3. Изменённый tasks.md прочитан полностью. Spec requirements/current acceptance,
   quickstart, data-model и contract дополнительно перечитаны в этом проходе.
   Новая T018 сверена с root-only decision в ранее прочитанном неизменном research.
4. Проверены active pointer и `check-prerequisites --json --paths-only`,
   фактические branch/HEAD; все указывают на F136. Канонический BRANCH без
   префикса в выводе скрипта не подменяет фактическую ветку.
5. Прочитан analyze-before-t018.json; его три document_sha256 совпали с текущими
   spec/plan/tasks. После reviewer notes оба checklist перечитаны и пересчитаны.

Области guidance/PRD/status, ранее прочитанные полностью или по относящимся
секциям, зафиксированы в предыдущем отчёте допуска. Конституция7.1.0 и
spec-kit-flow/product-gates были прочитаны полностью и остаются неизменными.
Нового исключения из требований их сверка не обнаружила.

## Обоснование обновлённого объёма

T018 не вводит новый способ входа и не закрывает OAuth provider-link. Она
устраняет несоответствие уже существующим FR002/003/005, SC002/003,
data-model и research: только корневые `/login` и `/sign-up` — auth documents
для безопасного повторного открытия; вложенные start/verify/callback legs
не становятся документами истории или источником SwiftUI GET.

Критерий проверяем и не требует смены server routes: разрешение существующей
route policy и живое отображение вложенного шага сохраняются, а сохранение
для будущего открытия запрещено. Нужно проверять три потребителя — безопасный
документ, безопасный history request и SwiftUI identity — плюс положительные
корневые страницы и отрицательные nested cases. Статус `authLogin`/`authSignup`
сам по себе не делает любой вложенный путь устойчивым документом.
Запрет replay не означает запрет текущего шага входа в WebKit.

T003 сохраняет архивную отметку, однако T018 явно фиксирует HIGH implementation
gap как новую открытую работу, с конкретными файлами, RED/GREEN и ссылкой на
требования. Анализ артефактов может иметь HIGH0, пока реализационный HIGH
остаётся открытым в tasks: это разные предметы проверки. Замалчивания долга нет.
Верхние описания прежнего среза не отменяют добавленную Phase7 Convergence.

Конституционные ограничения сохранены: native Record/Stop независимы,
серверные методы/providers/session storage/access не меняются, нет новых
секретов, инфраструктуры, сторонних ассетов или исключений из accessibility.
T004/T011/T012 OAuth и T016 GRAF Dev/manual остаются отдельными открытыми этапами.

## Повторная проверка всех checklist

По каждому R01–R16 и CHK001–CHK019 заново сверены его конкретные основания
из таблиц `checklist-recheck-before-stale-fix-20261018.md` с текущими
документами. Неизменность источников подтверждена таблицей SHA256; изменённая
T018 не опровергает ни один из этих пунктов.

| Пункты | Повторное основание | Решение |
|---|---|---|
| R01–R04 | Spec остаётся пользовательским и содержит обязательные sections/US1–3; новая задача не переносит детали кода в spec | 4 checked |
| R05–R08 | Clarifications полны; FR001–009 и SC001–004 по-прежнему однозначны, измеримы и не задают алгоритм | 4 checked |
| R09–R12 | Scenarios/edge cases/assumptions сохраняют scope и dependencies; T018 конкретизирует уже описанный root-only долг | 4 checked |
| R13–R16 | FR→US/SC/T mapping остаётся актуальным; T018 добавлена к safe-history/replay требованиям, не подменяя достигнутый результат | 4 checked |
| CHK001 | Key Entities + data-model Stable/Transient; root-only дополняет различие, отдельный новый CHK020 делает его явным | checked |
| CHK002–CHK004 | US1/US3/continuation/session table и Assumptions/FR007 по-прежнему различают primary/provider-link, все session transitions и серверные исключения | 3 checked |
| CHK005–CHK008 | FR001–007/US2/contract invariants сохраняют запрет replay, единую историю, порядок границы и normal navigation; T018 делает общее правило точнее | 4 checked |
| CHK009–CHK011 | US1/SC001–004/T016, edge cases/FR008 сохраняют способы входа, controls и ошибки/отмену/restart | 3 checked |
| CHK012–CHK015 | FR007/009, quickstart/contract ограничивают секреты, accessibility, server contracts и synthetic/manual evidence | 4 checked |
| CHK016 | Существующий срез с добавленной T018 остаётся отделён от T004/T011/T012/T016; архивные отметки не новая приёмка | checked |
| CHK017 | FR001/006/current acceptance сохраняют200/error/cancel без новой сессии и повторной формы | checked |
| CHK018 | FR004/contract сохраняют successful ordering, immediate401 и отклонение действительно старой identity; synthetic finding disposition не меняет requirement | checked |
| CHK019 | Research/quickstart отделяют исходный RED, последующий GREEN, native diagnostic и manual; T018 добавляет отдельный RED/GREEN | checked |
| CHK020 | Data-model явно допускает только root `/login`,`/sign-up`; research исключает action subpaths; contract invariant2 оставляет transient в живом WebKit; T018 называет историю и SwiftUI consumers | checked |

Добавлен один reviewer-owned пункт CHK020, проверяющий качество именно этой
границы, без отметки готовности кода. Старые checkbox не изменялись.

## Анализ и предшествующий полный набор

`analyze-before-t018.json`: PASS, 13 requirements,18 tasks, critical0/high0/
medium0, blocking_clarifications0, unmapped_tasks пуст. Реализационный root-only
HIGH явно учтён T018 и не объявляется закрытым этим анализом.
SHA256 анализа: `20c2a82410c2216ee720c7ad8ad46f250a5f91b6204182d5e83faea0459b7e86`.

Полный Swift перед T018: собственный разбор исходного graf-full-swift.log
подтвердил 1244 started/1244 unique,1242 PASS/2 SKIP/0 FAIL,97.519s.
Пропущены два необязательных экспорта изображений:
DesktopNotificationCardTests.testCardSurfacesCanBeCapturedForReferenceComparison
и SystemAudioPermissionUXTests.testRenderSyntheticPermissionStates.
SHA256 журнала: `b8a505a798dbd83353e0d620091b25bbe2605b7b47cd2a25bac8175e0881a341`.
Этот результат предшествует T018, не подтверждает её будущий код и не заменяет
новые тесты. Семь прежних AppKit/focus skips в этом запуске не повторились.

Спорный synthetic callback P2 снят как неподтверждённый продуктовый блокер
в `review-native-overlap-disposition-20261018.md`. Результат не переписан
как исправление кода; старые отчёты остаются историческими. Проверка T018
не меняет это решение.

## Итог после перечитывания

| Checklist | Checked | Unchecked |
|---|---:|---:|
| requirements.md | 16 | 0 |
| auth-navigation.md | 20 | 0 |
| Всего | 36 | 0 |

Менялись только два reviewer checklist и этот отчёт. Код, spec/plan/tasks,
GitHub, коммиты и чужие правки reviewer не затрагивал. Новые тесты не запускались.

## Снимок документов

Все записи, кроме tasks.md, совпали с ранее сохранёнными хешами.
Tasks прочитан полностью после изменения.

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
| specs/136-auth-navigation-recovery/quickstart.md | `3d3be9800e385c3e90e7b5568c022636bb41668c80e103818f09acdcc80bf5a1` |
| specs/136-auth-navigation-recovery/research.md | `5494a84d795102bf03f616b12d6f1dbe8acc905a5f5214a53ddb87fbef87c6b2` |
| specs/136-auth-navigation-recovery/data-model.md | `ea2683c1e7838b9d154508fac52f37e2b9f5098b4a443f3f793e164c257136ac` |
| specs/136-auth-navigation-recovery/contracts/cabinet-navigation-lifecycle.md | `fd3a209a57af6057c618d8667b64e62c97bf485db958d69f2665518a4929726f` |
| specs/136-auth-navigation-recovery/tasks.md | `cd38eba28b9ee11203b065506606a2514a9bd320fff1131708d44e251cb68d2c` |
