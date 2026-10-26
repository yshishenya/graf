# Независимое повторное ревью требований F228 — 26.10.2026

Проверяющий: `f228_requirements_recheck`. Полоса: существующая significant-feature,
подготовительное независимое ревью требований T009/#6247 и T019/#6257.
Исходный SHA: `2df314e5ca8549e636d386cdb68fecc861ddf015`; проверены также
незакоммиченные документы ветки `codex/228-pr-exception-fields`.

## Решение

**PASS качества требований: requirements 15 checked / 0 unchecked,
infra 6 checked / 0 unchecked; всего 21 checked / 0 unchecked.**
Открытых блокирующих неоднозначностей требований этого среза не найдено.
Это не PASS реализации, не приёмка полного US2/SC-003 и не основание закрывать
issues до профильных проверок, слияния и содержательной/live-проверки.

Сначала источники прочитаны в `/Users/yshishenya/.codex/worktrees/6484/crisp`.
После явной передачи основной агентом рабочая копия ревью перенесена в
`f228-requirements-audit/crisp`: совпадение исходных документов проверено
SHA-256; шесть изменённых документов прочитаны полностью заново.
Основная копия F273 не изменялась проверяющим.

## Устранённые ограничения и допустимый объём

1. Исходные зависимости `tasks.md` запрещали любую US2 до T005–T010.
   Это не было разрешением молча начать T019. До кода основным агентом явно
   уточнены plan/tasks/clarifications: самостоятельный T009/T019 проверяет
   только существующий текст спецификации/PR и не имеет входов из реестра или
   discovery. Зависимости остальных историй и критерии полного SC-003 сохранены.
2. В промежуточной редакции Status разрешал возобновление реализации, а Scope
   продолжал запрещать implementation commits и закрытия «этим этапом
   планирования». Финальный Scope отделяет историческое планирование от
   принятия T009/T019 после реализации, проверок и слияния. Запрет удаления,
   production и самоотметок чеклистов сохранён.
3. Конечное исключение определено однозначно: owner, expiry, reason,
   compatibility boundary, removal trigger, risk, validation, retirement task;
   каждое поле ровно одно, непустое и без шаблонной заглушки. Expiry — точная
   YYYY-MM-DD строго позже текущей даты UTC; retirement task содержит одну
   F###, одну T### и один #issue. Проверка формата не выдаётся за подтверждение
   существования или принятия будущего удаления.
4. Срез переиспользует существующую проверку `validate-legacy-impact.py`
   в существующем `validate-pr-metadata.py` из доверенной версии политики.
   Прежняя проверка единственной классификации обоих потребителей сохраняется.
   Новый реестр, сканер, сетевые запросы и запуск кода из PR не требуются.
5. Отдельные подтверждения коммита не являются новым условием: общее разрешение
   пользователя действует. Обязательные проверки точного SHA/основы остаются.

## Проверка каждого пункта

| Чеклист / пункт | Итог | Фактические источники требований |
|---|---|---|
| requirements CHK001 | PASS | spec US1/US3, FR-001/008/018 и registry contract§2 отделяют обнаружение от решения и разрешения удаления. |
| requirements CHK002 | PASS | FR-002–004, data-model LegacyContour/Evidence lifecycle, registry contract§1/3/4/6: поля, contained paths, metadata-only, SHA/digest/stale. |
| requirements CHK003 | PASS | FR-006, LegacyException, registry contract§5; clarifications «Срез T009/T019» уточняет восемь обязательных полей, конечную UTC-дату и единственные связи F/T/issue. |
| requirements CHK004 | PASS | FR-010–012/018, plan protected-domain matrix и retirement-slice contract сохраняют отдельные domain/rehearsal границы. |
| requirements CHK005 | PASS | LegacyContour и Evidence lifecycle, research: status/classification различаются, candidate/blocked до решения не получают классификацию, blocked→retired запрещён. |
| requirements CHK006 | PASS | FR-007, plan Taxonomy, T018: активная совместимость отличается от архивного evidence, исключения требуют rationale/owner. Эти требования остаются открытыми задачами реализации. |
| requirements CHK007 | PASS | FR-017/018, SC-008, финальный Scope, clarifications§6, plan и tasks сохраняют запреты удаления/production/самоотметок; исторический planning и T009/T019 явно разделены. |
| requirements CHK008 | PASS | F216 legacy-impact contract, FR-005/006/Assumptions: те же три классификации, конечное исключение и отдельные защищённые cutover-фичи. |
| requirements CHK009 | PASS | SC-001–008 проверяются metadata/синтетическими fixtures/отчётами; quickstart выделяет T009/T019 без объявления полного SC-003 готовым. |
| requirements CHK010 | PASS | Edge Cases: недоступность, stale, unsafe content, expired exception, missing owner/task/rollback явно блокируют дальнейшее действие; UTC/duplicates/placeholders уточнены. |
| requirements CHK011 | PASS | FR-010–012, plan matrix, T020–022/T036 и slice contract задают миграции, Temporal, MediaScribe, signing/appcast и deploy rollback. Репетиции этим ревью не проводились. |
| requirements CHK012 | PASS | US5/FR-016/SC-007, slice contract и F227 receipt/train contracts различают exact-PR checks и один Full замороженного фактического source SHA. |
| requirements CHK013 | PASS | US4/FR-014, plan Context, T026–028: root router, ignored pointer и scoped ссылки, без полного реестра в always-on контексте. |
| requirements CHK014 | PASS | FR-002/009/015/016, slice contract, T019/T030–032: task/issue/PR/SHA/fragment; root CHANGELOG остаётся у release operator. |
| requirements CHK015 | PASS | Actors/Assumptions/research: удаление требует owner/reviewer решения; discovery и отсутствие решения не дают такого разрешения. |
| infra CHK001 | PASS | FR-009/010, plan matrix, T020/023/024 требуют isolated backup/restore, expand/contract, abort/rollback, запрещают pointer mutation. |
| infra CHK002 | PASS | FR-011, matrix/T021, slice contract: replay/idempotency, history compatibility и запрет history deletion. |
| infra CHK003 | PASS | FR-012, matrix/T022: bundle ID, Developer ID/designated requirement, notarized rollback, appcast continuity и отдельный release gate. |
| infra CHK004 | PASS | FR-016/SC-007, F227 train/receipt contracts: frozen post-merge source, один authoritative Full; synthetic merge только provenance. |
| infra CHK005 | PASS | Actors/Scope/FR-018, clarifications§3, quickstart introduction: один изолированный Dev; текущий T009/T019 вообще не запускает приложение и не меняет production/volumes/TCC/secrets/signing. |
| infra CHK006 | PASS | FR-008–012, Edge Cases и slice contract: отсутствие protected-domain evidence или rollback блокирует срез без неявного исключения. |

## Отдельные ворота и пределы

Дополнительно прочитаны выгрузки `graf-f228-mapping36-20261026.json`,
`graf-f228-current-all.json`, исходные закрытия #6239–#6242 и PR #6313/#6790.
Карта содержит 36 различных task ID и 36 разных issue; ID каждой задачи
совпадает с ID в заголовке её issue. T036/#7741 присутствует, T009/#6247
и T019/#6257 открыты. Четыре подготовительные issue закрыты с отдельными
комментариями о принятии только подготовки. Метаданные подтверждают MERGED:
#6313 source `40d871f03f04ca56cd689d89902d6d46ab516cd9`, merge
`27a50f7e675aef60137a933f0599f5575efa5e5a`; #6790 source
`c061b21d8f4547b78ccdee9f09d5b392447a71d7`, merge
`0e7ebb7153bf6f1f00961f64f0f49d0ac4310f1f`.
Это независимое чтение предоставленных API-снимков, а не новый сетевой
запрос reviewer или повторная сертификация старого CI. Reviewer не меняет
task checkboxes или GitHub. Наличие `[X]` не подменяет отдельную
содержательную/live-приёмку issues.

`research.md`, data-model и контракты реестра/retirement остаются источниками
требований будущих задач. Их команды, protected-domain репетиции, выпуск и
production не выполнены этим ревью. Полный US2/SC-003 требует T010/T016–T018
и реестровой части. T034/T035 целиком также не принимаются этим срезом.

Для реализации требуются воспроизводимые RED/GREEN обоих потребителей,
проверки CLI и доверенного PR-пути, профильные проверки quickstart,
converge и затем GitHub `governance-fast`, `macos-pr`, `pr-metadata`
точного SHA/основы, общий валидатор PR и live closeout только принятых задач.
Reviewer не запускал тесты и не выполнял изменяющих состояние команд,
кроме разрешённых записей двух чеклистов и этого отчёта.

После записи оба чеклиста перечитаны целиком: requirements **15/0**, infra
**6/0**. Все прежние отметки `[x]` подтверждены заново; сами отметки не менялись.

## Прочитанные источники и SHA-256

Хеш идентифицирует прочитанное содержимое, а не выполненный критерий.
Ни память, ни отчёт другого агента не заменяли чтение.


| Прочитанный путь | SHA-256 |
|---|---|
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/development-process.md` | `1037b91f153f0757fff372e26cd05dd31433158c9c35d149125197a8a523f20d` |
| `docs/agent-guidance/codex-worktrees.md` | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| `docs/agent-guidance/tracker-policy.md` | `06450200cabdef48000af51241564e9ee9e8d36b50c71e06a88f8c50b7365466` |
| `specs/228-legacy-retirement-process/analysis.md` | `df8cffc0a42ffce9279a1598859c00a5e0491f96c57058768409f3b7beb75c64` |
| `specs/228-legacy-retirement-process/clarifications.md` | `dd331b7130bb17f1a9a2a6e917dc5ba6f8a04e39aee69dd1ce0316f7628ce69d` |
| `specs/228-legacy-retirement-process/data-model.md` | `fcb93c5b9dbbcb9d4d047ef2658eb2a29ab441bc5b133d9788fd974c9f7f699e` |
| `specs/228-legacy-retirement-process/plan.md` | `b2f69ee2e6ccd64857c62cb0ef3f91cb0314f9a80bec9050547d0ae72e606e1f` |
| `specs/228-legacy-retirement-process/quickstart.md` | `924ac763e2bedcba3e44c10500f904944aad034d72d3211c14290051b28019dd` |
| `specs/228-legacy-retirement-process/requirements-review-20261019.md` | `9c31ed3756a7db0e4f19a689f845c26d56b0b83bda0499deead05e1d827217b1` |
| `specs/228-legacy-retirement-process/research.md` | `83adcb8dc2fb53c1ffa11e32c97be16c936ee7f2382851d23fe3eefaac25506b` |
| `specs/228-legacy-retirement-process/spec.md` | `d9eae9534e7493b415e4fc2d772197bedcb06aa12416c748a9d8a55b30ab15a4` |
| `specs/228-legacy-retirement-process/tasks.md` | `7e212749055660e8beaed07835f48752ff66f7c16dd64437f94a4484fdc0957d` |
| `specs/228-legacy-retirement-process/checklists/infra.md` | `0227a7a7e2ad5b73c876a9c211a811d3351341418aec345692195334bc07f6af` |
| `specs/228-legacy-retirement-process/checklists/requirements.md` | `869846455cda070f7b55aa83c35219f30ad75933f325a57c016cdb8f4a578bec` |
| `specs/228-legacy-retirement-process/contracts/legacy-registry.md` | `db1c124da186c0c9a843621f914f80b0cebec411b81cd3b65351328da17f0c81` |
| `specs/228-legacy-retirement-process/contracts/retirement-slice.md` | `a155ee19a7cf3598b2bf818b8dd06f60e65a35726d2eaac6ecde8bc4a0161c02` |
| `specs/216-development-governance-harness/contracts/legacy-impact.md` | `6cbc646c8d8a933d34bd54e9cc5b881b4bed2f8b93b0655ad69dfb1fab5da0ee` |
| `specs/227-ci-merge-queue-release-train/contracts/ci-receipt.v1.md` | `9e6146a8aa70bdfb55fc59f39ac167862afcfe3fa61f3909e6abcb2bb8c02092` |
| `specs/227-ci-merge-queue-release-train/contracts/release-train.v1.md` | `b04a07030c32510dc25edb9a7fc2a1209c3979036ab8595c09a10fe29c9c9309` |

Из `release-and-validation.md` прочитаны применимые разделы Validation Lanes, Development-To-Release Workflow§1–2, Legacy Definition of Done, Git Safety и Evidence Safety; остальные release/runbook разделы не использованы для разрешения текущего среза.
