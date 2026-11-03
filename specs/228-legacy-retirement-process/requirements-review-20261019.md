# Текущий итог повторного независимого ревью F228 — 2026-10-19

**PASS качества требований: CRITICAL 0, HIGH 0.**
`requirements.md`: 15 checked / 0 unchecked; `infra.md`: 6 checked / 0 unchecked.
Все 21 пункт проверены повторно; прежние H1/H2 устранены. Это не завершение
36 задач F228 и не приёмка её issues. Исторический анализ и T036 issue sync
отдельно сверяет основной агент; остальные ворота до реализации сохраняются.

Ниже сохранён исходный BLOCKED первого прохода, его доказательства и хеши.
SHA-256 отчёта первого прохода до этого дополнения:
`89e14ac8f33cc6dcfcb928dc6db87e1a40734f886103c155b4c129c5f54960fc`.
Его формулировки «текущий»/«заблокировано» относятся к первому проходу.
Новый итог, отдельная таблица всех пунктов и новые хеши — в конце документа.

---

## Исторический первый проход — BLOCKED

# Независимое ревью качества требований F228

Дата: 2026-10-19. Исходный коммит: `5f712ba848cae1d7b0310f03c2fad52e126b9a04`.
Проверяющий: отдельный reviewer-агент `f228_checklists_review`.
Область: только качество требований двух reviewer-owned чеклистов перед реализацией.
Полоса: существующий significant/high-risk governance slice; это подготовительное
ревью, а не реализация, проверка работающего продукта или приёмка 32 issues.

## Решение

**BLOCKED: CRITICAL 0, HIGH 2.**

- `requirements.md`: 13 подтверждено, 2 открыто (CHK007, CHK009).
- `infra.md`: 6 подтверждено, 0 открыто.
- Всего: 19 подтверждено, 2 открыто из 21.

Каждый пункт проверен по содержанию требований. Код, spec, plan, tasks,
управляющие правила, GitHub, коммиты, выпуски и развёртывание не изменялись.
Тесты продукта не запускались: они не заменяют это ревью качества требований.

## Блокирующие замечания

### H1 — устаревший запрет любого изменения reviewer checkbox state

`spec.md` FR-017 запрещает automation/agents отмечать требования; SC-008
требует полного отсутствия изменения reviewer-owned checkbox state.
`clarifications.md` §6 повторяет запрет для агентов; `quickstart.md` §2 ожидает
все пункты unchecked; строка FR-017/SC-008 в tasks требует неизменных отметок.
Это расходится с действующей constitution 7.1.0, AGENTS.md и
`spec-kit-flow.md` §Checklist: независимый reviewer-агент обязан проверить
каждый пункт, отметить доказанные и вернуть проверенные totals, тогда как
агент реализации менять отметки не может. Обязательное независимое ревью
невозможно одновременно объявить отсутствием любых изменений отметок.

Нужно уточнить эти существующие требования и соответствующий критерий,
сохранив независимость reviewer и запрет реализации ставить свои отметки;
затем повторить анализ и независимое ревью изменённых требований. В этом
ревью spec/plan/tasks не исправлялись. Изменения двух чеклистов выполняются
в рамках прямого обязательного полномочия AGENTS/constitution, которое
имеет приоритет над историческим запретом F228.

### H2 — старое требование локального общего fast вместо полного текущего PR gate

`plan.md` §Validation Plan п.6, `quickstart.md` §5 и T034 предписывают
общий локальный `infra/scripts/ci-local.sh --fast` на PR-ready SHA.
План использует общее «exact-SHA fast CI», но ни эта программа, ни её
quickstart/task не закрепляют обязательную тройку GitHub `governance-fast`,
`macos-pr`, `pr-metadata` на точном head и проверенной основе с
`scripts/validate-pr-checks.py`. Текущее `release-and-validation.md`
требует именно её; общий локальный CI — только диагностика/резервный путь.

Нужно привести действующие план, quickstart и T034 к нынешнему процессу:
профильные локальные проверки → разрешённый коммит/PR → три обязательные
проверки текущего SHA/основы → общий валидатор. Локальный широкий fast
не становится новым обязательным вторым этапом. Это не основание
ослабить проверки или запускать Full CI для документального ревью.

## Доказательства по каждому пункту

Ссылки ниже относительно каталога F228; они указывают на требования,
а не на доказательство уже выполненной реализации.

| Чеклист / пункт | Итог | Основание |
|---|---|---|
| requirements CHK001 | PASS | spec US1/US3, FR-001/008/018, Scope; registry contract §2 отделяет discovery от разрешения удаления. |
| requirements CHK002 | PASS | FR-002–004, data-model LegacyContour/Evidence lifecycle, registry contract §1–6: поля, contained paths, запрещённый контент и смена SHA/digest. |
| requirements CHK003 | PASS | FR-006, data-model LegacyException и registry contract §5 требуют конечный срок, владельца, границу, риск, trigger и связанную работу. |
| requirements CHK004 | PASS | FR-010–012/018, plan Safe retirement protocol, retirement-slice contract требуют отдельные protected-domain границы. |
| requirements CHK005 | PASS | data-model LegacyContour/Evidence lifecycle разделяет status и classification, null до решения, candidate→approved→retired, запрет blocked→retired; research фиксирует владельца решения. |
| requirements CHK006 | PASS | FR-007 и plan Taxonomy перечисляют alias/fallback/flag/config/dependency/tests/docs/migration/Temporal/media/macOS, различают активное поведение и архив/negative evidence; исключения требуют reason/owner. T018 делает эти правила задачей реализации. |
| requirements CHK007 | OPEN | H1: no-removal/no-production согласованы; абсолютный no-reviewer-checkbox противоречит текущему обязательному независимому ревью. |
| requirements CHK008 | PASS | spec Assumptions/FR-005–007 и прочитанный F216 contracts/legacy-impact.md сохраняют один набор классификаций, конечные исключения и отдельные cutover features. Это не PASS всей исторической F216 или старого CI. |
| requirements CHK009 | OPEN | H1: SC-008 делает правильное независимое ревью недопустимым; остальные SC опираются на безопасные синтетические проверки, но требуется качество каждого SC. |
| requirements CHK010 | PASS | spec Edge Cases: недоступные GitHub/discovery → blocked, stale SHA/digest, unsafe metadata, expired exceptions, missing rollback → fail closed. |
| requirements CHK011 | PASS | FR-010–012, plan protected-domain matrix и T020–022/T036 задают migration restore, Temporal replay, MediaScribe cutoff/canonical/unavailable/cleanup, Sparkle identity/appcast и deploy rollback. Результаты этих будущих проверок не заявляются. |
| requirements CHK012 | PASS | US5/FR-016/SC-007 и retirement-slice contract явно различают индивидуальный fast и один frozen-candidate Full; F227 release-train contract подтверждает post-merge source SHA. Отдельный недостаток PR gate — H2. |
| requirements CHK013 | PASS | US4/FR-014, plan Agent and GitHub workflow, T026–028 требуют стабильный root router и одну scoped запись вместо полного реестра в контексте. |
| requirements CHK014 | PASS | FR-002/009/015/016, retirement-slice contract и T019/T030–032 требуют task/issue/PR/fragment/exact-SHA, root CHANGELOG принадлежит release operator. |
| requirements CHK015 | PASS | Actors, US1/US3, Assumptions и research сохраняют owner/reviewer решение удаления; обнаружение, отсутствие решения и отсутствие rollback не авторизуют removal. Ошибка полномочий независимого reviewer разобрана H1. |
| infra CHK001 | PASS | FR-009/010, protected-domain matrix, T020/023/024: isolated backup/restore, expand-contract, abort/rollback, запрет pointer mutation. |
| infra CHK002 | PASS | FR-011, matrix, T021 и retirement contract: deterministic replay/idempotency, history compatibility decision и no history deletion. |
| infra CHK003 | PASS | FR-012, matrix, T022: bundle ID, Developer ID/designated requirement, notarized rollback и appcast continuity; отдельный release gate. |
| infra CHK004 | PASS | US5, SC-007, release contract, F227 train contract: frozen exact post-merge source SHA и единственный authoritative Full, synthetic merge SHA — только provenance. |
| infra CHK005 | PASS | Actors/Scope/FR-018, quickstart introduction и clarifications §3 ограничивают единственный изолированный Dev, запрещают production/volumes/TCC/signing mutation. Текущий local-development.md сохраняет штатный harness и запрет ручных обходов. |
| infra CHK006 | PASS | FR-008–012, Edge Cases и retirement-slice contract прямо блокируют недостающую protected-domain evidence и rollback, вместо неявного продления исключения. |

## Исторические ограничения и повторная проверка

`analysis.md` от2026-09-01 описывает прежний baseline. Его вывод «0 findings»
не заменяет текущий анализ после изменения constitution и CI-процесса.
В нём также осталось 35 tasks, тогда как текущий tasks содержит T001–T036
(36): T036 явно добавляет MediaScribe-доказательства. Это MEDIUM M1:
обновить анализ/traceability после устранения HIGH, не переписывая историю
и не объявляя августовские observed candidates сегодняшней инвентаризацией.

Исходный локальный pointer отсутствовал. Для чтения использован прямо
допущенный `codex-worktrees.md` явный anchor:
`SPECIFY_FEATURE_DIRECTORY=specs/228-legacy-retirement-process
.specify/scripts/bash/check-prerequisites.sh --json --paths-only`.
Команда разрешила существующие F228 пути без изменения pointer. Перед
реализацией основной агент должен восстановить согласованный active context;
это ревью не выбирало фичу по имени физического каталога или времени файла.

После записи оба чеклиста перечитаны целиком. Их totals посчитаны по строкам
с `CHK###`; незавершённые пункты имеют конкретные причины выше.
Разрешены только уточнение требований и повторный анализ/ревью; реализация
до устранения HIGH и получения полного PASS не разрешена.

## Полностью прочитанные документы и SHA-256

Хеш фиксирует прочитанные байты; он не доказывает реализацию требований.
Ни память, ни отчёты других агентов не заменяли чтение.

| Путь от корня репозитория | SHA-256 |
|---|---|
| `AGENTS.md` | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `docs/agent-guidance/README.md` | `e892c6ae7fe7ce92ff35f8836c5dd58ce5753402a725c78dbbc86c46da11cc67` |
| `docs/agent-guidance/codex-worktrees.md` | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| `docs/agent-guidance/spec-kit-flow.md` | `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/development-process.md` | `4328c0341ec6fd354f3855ed8da4902949e18d87063e3fb428dd414715ddcdd7` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/agent-guidance/release-and-validation.md` | `e3d24689a330634ec5ef87d829f8bcbf16bb7b81e0196b9d0baae4f49f27278d` |
| `docs/agent-guidance/local-development.md` | `0c2952b5a774f304871db0def94a5f4269f46b39e539215a36d986344476eb50` |
| `specs/228-legacy-retirement-process/analysis.md` | `8453a3ee9c551b3b4f04f7144fd901d9ce93dd995de8eae56e56d7d88bc109a3` |
| `specs/228-legacy-retirement-process/checklists/infra.md` | `d3eb82f1218a91182a097186f083040460330542bb93ceff0f0252e74a754fca` |
| `specs/228-legacy-retirement-process/checklists/requirements.md` | `53e7154c17faab91a62b2af73cc41b0eb2a9f1430ba8ca10c5992c0207014a6d` |
| `specs/228-legacy-retirement-process/clarifications.md` | `98c590dacd0a915ab3589fdac04f0f8ef1b48cc3b08c1f2e83cb4691d738f4a5` |
| `specs/228-legacy-retirement-process/contracts/legacy-registry.md` | `db1c124da186c0c9a843621f914f80b0cebec411b81cd3b65351328da17f0c81` |
| `specs/228-legacy-retirement-process/contracts/retirement-slice.md` | `a155ee19a7cf3598b2bf818b8dd06f60e65a35726d2eaac6ecde8bc4a0161c02` |
| `specs/228-legacy-retirement-process/data-model.md` | `fcb93c5b9dbbcb9d4d047ef2658eb2a29ab441bc5b133d9788fd974c9f7f699e` |
| `specs/228-legacy-retirement-process/plan.md` | `bb3b2618c2d9759844c22f862c2c87cdccb584d66cb9e039000c3e6172c03a8f` |
| `specs/228-legacy-retirement-process/quickstart.md` | `eb5dee81b7788f63ffc30c578bcbf1faa75b2f7fbb878528f5a388f203cb4387` |
| `specs/228-legacy-retirement-process/research.md` | `83adcb8dc2fb53c1ffa11e32c97be16c936ee7f2382851d23fe3eefaac25506b` |
| `specs/228-legacy-retirement-process/spec.md` | `060b1ffe9fba6002b1773f7f729294030acbde4de4751641b50796f87504aba5` |
| `specs/228-legacy-retirement-process/tasks.md` | `15b63e9335e32916eddbff30b82e7a461d8968216cfd2ea3bc043942be8c284a` |
| `specs/216-development-governance-harness/spec.md` | `8d2296f74e575ffe6d2be523a97220266dfdc34f40d6963eaf753f9816993cd2` |
| `specs/216-development-governance-harness/contracts/legacy-impact.md` | `6cbc646c8d8a933d34bd54e9cc5b881b4bed2f8b93b0655ad69dfb1fab5da0ee` |
| `specs/227-ci-merge-queue-release-train/contracts/ci-receipt.v1.md` | `9e6146a8aa70bdfb55fc59f39ac167862afcfe3fa61f3909e6abcb2bb8c02092` |
| `specs/227-ci-merge-queue-release-train/contracts/release-train.v1.md` | `a2da03c77153f9fac0cc17493c44084877b4b2e322b0f6663bf36f17fc516e56` |


---

## Повторный проход после уточнения требований — 2026-10-19

Источник Git остался `5f712ba848cae1d7b0310f03c2fad52e126b9a04`, ветка
`codex/228-requirements-audit`; проверены именно локально изменённые байты.
Согласованный ignored pointer теперь существует и явно связывает F228,
ветку, source SHA и owned paths. Его prerequisite разрешил существующие
пути; имя BRANCH в JSON resolver остаётся производным от feature directory
и не используется вместо фактической `git branch --show-current`.

Пять изменившихся документов (`spec.md`, `clarifications.md`, `plan.md`,
`tasks.md`, `quickstart.md`) прочитаны полностью. Хеши всех остальных 23
ранее прочитанных документов совпали, и их полное содержание доступно
в том же диалоге; использовано правило document-reading.md без подмены
чтения совпадением Git SHA. Затем оба изменённых чеклиста перечитаны полностью.

### Разрешение замечаний

- **H1 RESOLVED:** Actors, FR-017, SC-008, Scope, clarifications §6,
  plan Constitution Check/Validation Plan, quickstart §2 и T033/traceability
  согласованно закрепляют независимое ревью до реализации, доказательные
  отметки, открытые причины, повторное чтение и totals. Агент реализации
  отметки не меняет. SC-008 теперь измерим и не конфликтует с constitution7.1.0.
- **H2 RESOLVED:** plan Workflow/Implementation Approach/Validation Plan,
  quickstart §5 и T034 требуют `governance-fast`, `macos-pr`, `pr-metadata`
  на точном SHA/проверенной основе и общий валидатор. Общий локальный fast
  явно диагностический; отдельный release-full по frozen candidate сохранён.
- Дополнительно проверено: T020/T021/T022/T036 больше не имеют `[P]`,
  dependencies требуют их последовательного выполнения до T023, поскольку
  они меняют один файл. Это согласует планирование без выполнения этих задач.
- **M1 остаётся историческим/учётным ограничением:** старый analysis35 не
  выдаётся за текущий анализ36; наличие live issue T036 не проверялось этим
  reviewer. Это отдельная сверка основного агента до реализации. Ни одной
  task checkbox reviewer не менял.

### Повторная таблица качества требований — все пункты

| Чеклист / пункт | Итог | Текущее доказательство |
|---|---|---|
| requirements CHK001 | PASS | spec US1/US3, FR-001/008/018, Scope и registry contract§2 по-прежнему разделяют обнаружение, классификацию и право удаления. |
| requirements CHK002 | PASS | FR-002–004, неизменные data-model/registry contract: обязательные metadata-only поля, contained paths, SHA/digest stale. |
| requirements CHK003 | PASS | FR-006 + LegacyException + registry§5 сохраняют owner/expiry/trigger/risk/validation/task для каждого исключения. |
| requirements CHK004 | PASS | FR-010–012/018 и plan protected-domain matrix сохраняют отдельные safety/rehearsal границы. |
| requirements CHK005 | PASS | LegacyContour/Evidence lifecycle и research сохраняют status/classification и запрет blocked→retired. |
| requirements CHK006 | PASS | FR-007 + plan Taxonomy + T018 ограничивают активную совместимость и архив, исключения требуют rationale/owner. |
| requirements CHK007 | PASS | Исправленные FR-017/SC-008/Scope, clarifications§6, plan, quickstart§2, T033/traceability: отдельный reviewer действует по evidence; реализация не меняет отметки. Удаление/production по-прежнему запрещены. |
| requirements CHK008 | PASS | FR-005–007/Assumptions и F216 legacy-impact contract не меняют общий контракт; изменения роли reviewer согласованы с constitution7.1.0. |
| requirements CHK009 | PASS | SC001 поля/пути, SC002 digest, SC003 синтетические исключения, SC004 связи/blocked reason, SC005 domain category, SC006 context, SC007 immutable receipt и новый SC008 diff/ownership/review report проверяемы на безопасных metadata/fixtures. |
| requirements CHK010 | PASS | Edge Cases сохраняют явные blocked/stale/unsafe/expired/missing rollback и fail-closed поведение. |
| requirements CHK011 | PASS | FR-010–012, domain matrix, T020–022/T036 и slice contract сохраняют domain-appropriate доказательства всех пяти областей. |
| requirements CHK012 | PASS | US5/FR-016/SC007, slice/F227 train contracts и обновлённые plan/quickstart сохраняют разделение PR proof и frozen-candidate Full. |
| requirements CHK013 | PASS | US4/FR014 + plan Context + T026–028 задают scoped read set и стабильный root router без полного реестра. |
| requirements CHK014 | PASS | FR002/009/015/016 + slice contract + T019/T030–032 сохраняют issue/task/PR/fragment/SHA, root changelog — только release operator. |
| requirements CHK015 | PASS | Actors/Assumptions/research сохраняют owner/reviewer decision для удаления; уточнённая роль reviewer не даёт реализации права авторизовать removal. |
| infra CHK001 | PASS | FR009/010, matrix, T020/023/024: isolated backup/restore, expand-contract, abort/rollback, no pointer mutation. |
| infra CHK002 | PASS | FR011, matrix, T021, slice contract: replay/idempotency/history compatibility/no history deletion. |
| infra CHK003 | PASS | FR012, matrix/T022: identity, Developer ID/designated requirement, notarized rollback/appcast continuity, отдельный release gate. |
| infra CHK004 | PASS | US5/SC007 + release/F227 contract: exact frozen post-merge source SHA, один Full, synthetic merge SHA — provenance. |
| infra CHK005 | PASS | Actors/Scope/FR018 + quickstart/clarifications§3 и local-development: один Dev и запрет production/volume/TCC/credential/signing mutation. |
| infra CHK006 | PASS | FR008–012, Edge Cases/slice contract: missing rollback/domain evidence блокирует slice без неявного исключения. |

### Итог повторного чтения

- requirements: **15 checked, 0 unchecked**.
- infra: **6 checked, 0 unchecked**.
- Итого: **21 checked, 0 unchecked**. Новых CRITICAL/HIGH не найдено.

PASS снимает замечания именно к качеству этих требований. Он не заменяет
новый analysis, синхронизацию issues, профильные тесты реализации, отдельное
разрешение на проверенный коммит, GitHub exact-SHA/base checks, выпуск или
развёртывание. Runtime/data/history удаление F228 по-прежнему не разрешает.

### Новые хеши повторно прочитанных/изменённых документов

| Путь от корня | SHA-256 |
|---|---|
| `specs/228-legacy-retirement-process/spec.md` | `fc9c217aa20f09015356524f6a2b5c02058fcc93ef514829a8bab27bb75da3ad` |
| `specs/228-legacy-retirement-process/clarifications.md` | `0d51e764b0729697644f9df3ead1080860689ba77faab828500da9bd7d91a800` |
| `specs/228-legacy-retirement-process/plan.md` | `1843b3ba715764dd3b8d2216c5113469071f7af9039f395be8cd7c6f9c939b11` |
| `specs/228-legacy-retirement-process/tasks.md` | `24b970c08d3423ef4e60e57865c8f26bcbbc83b6f56b8e694e32e640987711ac` |
| `specs/228-legacy-retirement-process/quickstart.md` | `0cfcdeee6357fcda73ccac1664462c603b8ad968a773d869bfc6d9b7c780b4ec` |
| `specs/228-legacy-retirement-process/checklists/requirements.md` | `fe6301d18487cdda097fd16108026d2d97665f3b40b22226116517b6dbf653ea` |
| `specs/228-legacy-retirement-process/checklists/infra.md` | `29b99be0f1c799169fba13fa2d82ef41e5dd15e113f5c845c9c836765cc97282` |

Хеши остальных прочитанных документов совпадают с исторической таблицей первого прохода.


## Финальная сверка планового T033 — 2026-10-19

Полностью перечитаны изменённые `tasks.md` и `analysis.md`. Последние хеши
остальных 26 ранее прочитанных документов проверены и совпали; содержание
сохраняется в том же диалоге. Оба чеклиста перечитаны полностью: requirements
**15 checked / 0 unchecked**, infra **6 checked / 0 unchecked**.

**PASS качества требований сохраняется, CRITICAL 0 / HIGH 0.**
Текущий анализ охватывает 36 уникальных task IDs и явную связь T036 с
MediaScribe-границей. Историческое тело анализа сохранено побайтно, кроме
его явно изменённого исторического заголовка; выполнено сравнение с HEAD.
Прежнее замечание M1 к актуальности анализа устранено новым разделом,
без переписывания старого результата35.

По строкам `tasks.md` отмечена ровно **T033 / Issue #6271**; остальные
**35 задач остаются `[ ]`**. Анализ и независимое ревью обеспечивают локальный
плановый результат T033. Это не подтверждение текущего GitHub-состояния #6271,
не разрешение его закрыть до обязательных exact-SHA/base и live-проверок
и не завершение остальных задач или всей F228. Предупреждение о необходимости
сверить T001–T004 closed/unchecked и владельца T036 оставлено явно; реализация
до обязательной синхронизации task/issue не разрешена. Reviewer не проверял
и не изменял GitHub и не менял task checkbox.

В этом финальном проходе изменён только этот отчёт. Чеклисты, analysis/tasks,
код/runtime/production не изменялись reviewer-агентом. `git diff --check` PASS.

| Повторно прочитанный путь | SHA-256 |
|---|---|
| `specs/228-legacy-retirement-process/tasks.md` | `0dcf604a0ed296548d3de643ee0abdc5e12f94a2d34b0dec89f76d50c96c9e15` |
| `specs/228-legacy-retirement-process/analysis.md` | `a2d9458d2da5de5f2ee6ebfbf3baeb6838a20ddc3bf40960016c13b1351990ab` |
