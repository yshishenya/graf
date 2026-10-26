# Независимое повторное ревью F216: требования и итоговая приёмка

Дата: 26.10.2026. Reviewer: отдельный агент `f216_checklist_recheck`.
Основа: `ac81b17f193469a18f661eafd0d1fd5c4f86d29b`;
ветка `codex/216-requirements-reconciliation`. Документы проверены с рабочими
изменениями поверх этой основы; это не доказательство будущего SHA коммита.

Область: документальный срез существующей F216/T036–T037; исходники продукта,
общие правила, CI, приложения, стенды, Git и GitHub не изменялись reviewer.
Разрешённые изменения reviewer: два checklist и этот отчёт.
AGENTS, индекс guidance, конституция, spec-kit-flow и release-and-validation
совпадают с прочитанными при первом независимом ревью; совпадение проверено
через Git. Изменившиеся tracker-policy/development-process перечитаны по diff.
Прочитаны исправленные spec/plan/tasks/research/quickstart, data-model и contracts.

## Решение и пределы

Качество требований: **PASS, 16/16**. При проверке согласованности именно
исправленного документального среза после замечания к T039:
**Critical 0 / High 0**. Это независимая содержательная проверка; она не
объявляет завершёнными converge и приёмку всей F216. Итог T037 описан
отдельно в `reconciliation-20261026.md`; закрытие issue требует принятого PR
и live-проверки.

Итоговая приёмка F216: **BLOCK**, предметные критерии **19/23**, ещё **4**
не подтверждены. Вместе с тремя альтернативами решения `governance.md` имеет
**20 checked / 6 unchecked**; отмечена только альтернатива BLOCK.
Решение о полном закрытии #6125/T036, T047 или umbrella этим отчётом не дано.

Сохранены все исходные 16 требований и 23 предметных критерия. В governance
уточнены назначение итоговой приёмки и dry-run только изменяющим состояние
операциям по уже существующему `contracts/dev-manifest.md`. Ни одно требование
к работающему стенду, разрешениям, конкурентности, откату или публикации
не удалено. PASS качества требований не превращает открытые критерии в PASS.

## Проверка требований

R1–R16 следуют исходному порядку `checklists/requirements.md`.
Ссылки ниже относительно каталога F216, если не назван корень репозитория.

| Пункт | Оценка | Конкретное основание |
|---|---|---|
| R1 Нет лишних деталей реализации в пользовательских сценариях | PASS | spec: US1–US8 описывают наблюдаемый результат технических участников; архитектура отдельно в plan/contracts. |
| R2 Описана ценность для владельца, агента, reviewer и operator | PASS | spec: Actors and Goals, US1–US8. |
| R3 Текст понятен участникам без знания внутреннего кода | PASS | Новый раздел spec «Термины» объясняет claim, pinned version, metadata-only evidence, immutable candidate и authoritative Full CI. |
| R4 Все обязательные разделы шаблона заполнены | PASS | spec: роли, сценарии, отказы, FR, сущности, Clarifications, Scope, SC, Assumptions, Legacy Impact. |
| R5 Нет нерешённых маркеров NEEDS CLARIFICATION | PASS | Полное чтение spec и поиск незавершённых маркеров; Clarifications содержит решения. |
| R6 Требования проверяемы и однозначны | PASS | FR-011 согласован с CLI-контрактом; FR-022/SC-009 требуют настоящие GitHub checks; FR-033 сохраняет выключенные hooks и проверку/сходимость перед коммитом. |
| R7 Success criteria измеримы и проверяются без скрытых допущений | PASS | SC-003 различает изолированный тест и реальную приёмку; SC-005 проверяет механизм публикационной записи без заявления выпуска; SC-009 явно оставляет реальную Dev-приёмку обязательной. |
| R8 Описаны позитивные, конкурентные и отказные сценарии | PASS | US1/US2/US4: одновременная работа; US2: частичный отказ; US3: stale/interrupted; Edge Cases. |
| R9 Границы In Scope / Out of Scope явны | PASS | spec: Scope; plan: Release Gate/no deploy; продуктовая публикация не входит. |
| R10 Assumptions и зависимости зафиксированы | PASS | spec: Assumptions and Dependencies; Actions обновлены до текущего обязательного GitHub-пути. |
| R11 Legacy Impact и follow-up boundary зафиксированы | PASS | spec: FR-026–029, Legacy Impact; contracts/legacy-impact отделяет форматный валидатор от проверки потребителей. |
| R12 Каждый user story независимо тестируем | PASS | Все восемь Independent Test сохранены; US2 теперь требует отдельное реальное доказательство и сначала проверку F229/F249. |
| R13 Worktree, Feature ID, Dev, CI, release и harness имеют трассируемые критерии | PASS | FR-001–036, SC-001–010 и ссылки в tasks покрывают все шесть областей. Это трассировка требований, не доказательство полной синхронизации issues. |
| R14 Reviewer-owned checklist не смешан с implementation DoD | PASS | requirements проверяет качество текста; governance явно стал итоговой приёмкой уже реализованной F216 и не разрешает начать реализацию задним числом. |
| R15 Требования не ослабляют constitution, product gates или public signing rules | PASS | plan Constitution Check; scope исключает продуктовую публикацию; FR-022/SC-009/contracts требуют актуальные GitHub проверки; Dev-приёмка сохранена. |
| R16 Отдельный reusable repository имеет provenance, versioning и secret/path boundary | PASS | FR-030/031; US8; contracts/harness-package: Publication gate/Compatibility; quickstart закрепляет v0.1.13/точный commit и возврат v0.1.12. Здесь оценено качество требований, а не выпуск. |

## Итоговая предметная приёмка

G1–G23 следуют исходному порядку `checklists/governance.md`. «Подтверждено»
ниже ограничено указанным источником: код защитного механизма не выдаётся за
проверку работающего приложения. Неподтверждённость не означает найденный дефект
и сама по себе не требует повторять ранее принятые или переданные сценарии.

| Пункт | Оценка | Источник / недостающее доказательство |
|---|---|---|
| G1 Feature ID 216 не пересекается с локальными/remote refs, issues и PR | Подтверждено в видимых источниках | Один каталог F216; текущая ветка codex/216-requirements-reconciliation; удалённых *216* heads нет. Первая live-проверка выявила основной PR #6142 и общий релизный #6336, не две разные инициативы. |
| G2 Umbrella #6090 связан со всеми task-backed issues | Подтверждено после исправления | Финальная повторная live-выгрузка: 60 issues с единственными T001–T060, все body ссылаются #6090; T054 → #7748 OPEN, T060 → #6090 OPEN. Изначальный пропуск T054 и T000 родителя исправлены исполнителем; reviewer состояние не менял. |
| G3 feature.json — единственный active pointer; mtime fallback отсутствует | Подтверждено в проверенном механизме | Корневой scripts/validate-agent-context.py:23–79 отклоняет отсутствие/повреждение pointer, сверяет directory/ID/branch/SHA; AGENTS managed block закрепляет источник. |
| G4 Root AGENTS стабилен и не содержит текущий task | Подтверждено | Весь AGENTS прочитан, текущего task там нет; Git подтвердил отсутствие изменений по сравнению с первым ревью. |
| G5 Один agent/worktree имеет одного owner и один branch | Открыто | Политика и owner текущего feature.json имеются; соблюдение во всех действующих worktree не инвентаризировалось. |
| G6 Changelog fragment namespace уникален; root CHANGELOG — release operator | Подтверждено для механизма | changes/unreleased/README.md:3–5,21–23 и валидатор namespace; F216 архивирован в changes/releases/v2026.09.01.1/. Авторство каждого исторического изменения не заявляется. |
| G7 Auto-commit hooks не создают неожиданные implementation commits | Подтверждено для конфигурации | .specify/extensions.yml:94–200: speckit.git.commit hooks enabled:false. |
| G8 Evidence metadata-only без secrets/private content | Открыто для полного набора | Изученный документальный diff содержит только правила/версии/ссылки; полный набор внешних исторических runtime/release артефактов не проверен. |
| G9 Изменяющие операции имеют dry-run, все операции fail closed | Подтверждено изолированными проверками | contracts/dev-manifest и FR-011 согласованы с CLI. Прочитан focused-tests.log: 52 PASS для четырёх файлов quickstart, включая dry-run/reset confirmation, отказ при mismatch/production boundary и частичной активации. Реальная Dev-приёмка остаётся G10/G12/G18. |
| G10 Один active manifest и SHA backend/frontend/app | Подтверждено исторической приёмкой преемника | F249 #6786, комментарий 5586487199: 08.09.2026 active manifest dev-e81b412dff92, установленное приложение и runtime соответствуют e81b412dff920cc29ed37de60be13dd8fc4d1c43, schema0089, smoke13/13. F229 #6276, комментарий 5514328306: все девять фактических image IDs совпали с выбранными manifests; final dev-4d9d579c65e8 exact SHA PASS. Это не проверка текущего стенда 26.10.2026. |
| G11 Promote lock/atomic activation доказаны конкурентным тестом | Подтверждено изолированным тестом | Независимо прочитан журнал 52 PASS, проверены исходники test_concurrent_promote_is_serialized и test_dev_promotion_transaction.py; блокировка/порядок публикации активного указателя покрыты. Это не факт приёмки работающего установленного стенда. |
| G12 GRAF Dev.app сохраняет bundle/signing/designated requirement/permissions | Подтверждено исторической установленной проверкой | F249 implementation-evidence.md:518–526: на 6fefaeb5b68adcd4fd30ca0d5f447b9114891398 штатные build/promote/status/smoke, активный manifest, все 13 пунктов pass; bundle ID, подпись, designated requirement, entitlements и разрешения сохранены. Принятие этих установленных проверок дополнительно записано в закрытии #6786. Не заявляется текущая проверка разрешений или новая установка. |
| G13 Dev reset не может затронуть production | Подтверждено для нынешней операции | scripts/dev-harness.py:3322–3346: подтверждение, Dev guard, lock, запрет сброса живого/общего состояния; удаляется только Dev active pointer, scope=metadata-only-dev-state. |
| G14 Stale SHA не считается evidence | Подтверждено для валидатора | scripts/validate-ci-evidence.py:138–152 отклоняет несовпадающие requested/start/end SHA и failed/stale/cancelled/ambiguous. |
| G15 Frozen candidate допускает один authoritative Full CI | Подтверждено для принятия доказательства | infra/scripts/release-candidate.sh:1087–1129,1175,1214–1229: immutable identity, канонический evidence, проверка GitHub run и запрет перезаписи. Не заявлено отсутствие отдельных диагностических запусков. |
| G16 Fast/full границы и cancellation описаны в templates | Подтверждено | .github/pull_request_template.md:21–39; release-and-validation:25–64; исправленный contracts/ci-release.md. |
| G17 CalVer/tag/GitHub Release/Russian notes связаны с exact SHA | Подтверждено прямыми сохранёнными ответами GitHub | Release382716588 опубликован 04.09.2026, draft/prerelease false, русский body; tag v2026.09.04.1 → annotated object d40fd94cf943c7eb8ba4b66809031a3e89ca328b → commit704a374f0eee454fa41e7bd820154c900cd0e910. Это тот же Candidate SHA и Release URL принятого закрытия F229/#6276/5541569686 с release-full33869861986. Проверен исторический выпуск, новый выпуск не выполнялся. |
| G18 Rollback и skipped gates имеют metadata-only evidence | Частично подтверждено; пункт остаётся открытым | Реальный rollback/компенсация приняты F229 #6276/5514328306 и F249 #6786/5586487199; F249 implementation-evidence.md:478–498 сохраняет SHA, schema, smoke13/13 и совпадение digest без содержимого данных. Полной записи пропущенных gates с command/start/end/status/scope/skipped/reason по FR-035 в прочитанном наборе нет. Реальный откат повторять не требуется. |
| G19 Legacy Impact обязателен в spec и PR | Подтверждено | spec Legacy Impact, PR template:53–72, validate-legacy-impact.py:62–80 отклоняет отсутствие/дубли/неверный classification. |
| G20 Исключения имеют owner/expiry/trigger/retirement task | Подтверждено для контракта | validate-legacy-impact.py:21–58: единственность и непустота полей, будущая UTC-дата, F/T/#issue. Формат не доказывает принятую миграцию. |
| G21 Existing legacy cleanup отдельно в Feature 217+ | Подтверждено как разделение объёма | Отдельная specs/228-legacy-retirement-process/; F216 Scope исключает массовое удаление. Это не приёмка всех задач F228. |
| G22 Generic harness отделён от GRAF product gates | Подтверждено по структуре/контракту | harness/AGENTS.md:3–5,16–17, harness/README.md и contracts/harness-package.md:3–13 оставляют product/privacy/signing/deploy в адаптере. |
| G23 Публикация reusable repo блокируется при secret/path/provenance нарушении | Открыто полностью | package_safety в harness/src/dev_harness/validators.py:452–486 проверяет секреты/пути/генерируемые файлы; contract требует provenance/license. Полный gate конкретного внешнего выпуска этим ревью не проверен. |

## Проверка согласованности и остаток

Замечание к новому diff: ранее отмеченная T039 сначала была переписана под
новые три GitHub-проверки, что создавало неподтверждённое новое утверждение
о выполнении. После замечания исполнитель восстановил историческое описание
локального fast и явно отнёс текущие GitHub gates к T047. Исправление перечитано;
замечание снято. Грамматический стык T002 также исправлен.

После чтения дополнительных доказательств исполнитель восстановил [X]
для T034/T050/T051/T053: чистый consumer/upgrade/rollback, неизменяемая
публикационная запись, digest фактических тестовых файлов и опубликованный
v0.1.13 подтверждены названными ниже журналами и существующими тестами.
Повторный diff tasks перечитан. T048/T052 сохранены [ ] с явным NOT_PLANNED
и преемниками F229/F249; отмена не подменена выполнением. Добавленная T060
остаётся [ ] и отдельно владеет сверкой. Исполнитель создал #7748 для T054
и заменил T000 родителя на T060; reviewer независимо подтвердил новый live
набор 60 задач/60 единственных issues. Завершение самих issues этим не заявлено.
В нём не заявлена полная приёмка F216. Окончательная сверка закрытых issues и исходных [ ],
подтверждение действующих преемников F229/F249, полные runtime/release
доказательства остаются T040/T047 и соответствующим задачам. Это известный
остаток исходной фичи, а не новая реализация или разрешение повторно открыть
уже закрытые задачи без содержательной проверки.

Команды reviewer: git status/rev-parse/diff; чтение и поиск по названным
документам/источникам; gh issue list по feature:216; git branch и ls-remote;
подсчёт исходных/итоговых checklist и контрольных сумм. Все GitHub команды
только читали состояние. Reviewer сам тесты/пакет не запускал. Независимо
прочитаны фактические журналы
исполнителя и указанные ниже исходники. Последующая проверка сохранённых
преемников отдельно принимает исторические manifest/SHA и сохранение
идентичности/разрешений; текущий живой стенд этим не проверяется.

## Финальная повторная сверка

После сообщения исполнителя о завершении документов повторно прочитаны
`reconciliation-20261026.md`, окончательный diff `tasks.md` и фрагмент
`changes/unreleased/F216.yaml`. Таблица анализа охватывает FR-001–036 и
SC-001–010, согласуется с их задачами; T037 [X] отражает анализ, а не
фактическую Dev-приёмку. T036/T040/T047/T060 и umbrella остаются открытыми.
Четыре восстановленных [X] поддержаны прочитанными проверками; две отмены
сохраняют [ ]. Текущий T039 не присваивает историческому локальному fast
новые GitHub-доказательства. Сверка не меняет code/CI/общие правила и
не разрешает выпуск/production. Неразрешённых Critical/High замечаний
к этому окончательному документальному набору нет; предметный BLOCK сохранён.

Фрагмент описывает только нынешнюю сверку, T037/T060 и открытый остаток;
исторические выпущенные записи не возвращены в unreleased.

## Дополнительные прочитанные доказательства исполнителя

- `focused-tests.log`: 52 passed in 44.65s; четыре существующих файла из
  quickstart (Dev harness, promotion transaction, CI producer, release candidate).
  Код и эти тесты не изменены документальным diff относительно основы.
- `harness-checks.json`: внешний tag v0.1.13 разрешён в
  `6a8257186aee878087b68fd77716ddce595a012d`; source self-test/sample/package/context
  имеют exit 0. Опубликованные wheel/tar совпали с опубликованными суммами:
  `75214c9919bd94aba7410dd3aa0ab7c0657ac4e644838903fadf0850ec46e321` и
  `1d074a26c7a032c70c17352c02bbca978a26b0476b75b2ace63b7980e113f844`.
  Reviewer отдельно прочитал временный source, проверил HEAD, MIT LICENSE,
  version/pyproject и `.github/workflows/self-test.yml`: package scan стоит
  до сборки. Это не полный аудит происхождения всего внешнего проекта.
- `harness-upgrade-rollback.json`: installed version/self-test/sample PASS
  при v0.1.12 → v0.1.13 → v0.1.12. Предыдущий wheel собран из immutable tag
  `9ba1f6e616103782b2e93f9752db98cee913dcc6`; у старого GitHub Release нет
  двоичных assets, поэтому его wheel не объявлен опубликованным.
- `attestation-check.json` и прочитанный `check-attestation.py`: отдельная
  публикационная запись с правильными SHA/tag/URL создана; три несовпадения
  и две повторные записи отклонены, decision и publication неизменны. GitHub
  подменён искусственными ответами; реальных Full CI/tag/Release/CD не было.

Имена ниже идентифицируют локальные журналы исполнителя; исходные журналы
остаются вне git, их содержимое с временными машинными путями сюда не копируется.

| Прочитанный журнал | SHA-256 |
|---|---|
| focused-tests.log | `742ce98ee5ad45c68d31c4222863961edbb6a1d3fc206c8325d129af4276af5b` |
| harness-checks.json | `bddfd4d890d79b390a9b4937b7e603e8aeff8d672f596d8b558b415086988ed5` |
| harness-upgrade-rollback.json | `a9d21a62eb7bac7b417957eef98520c5e0a815f0e16346108cac813387a08b50` |
| attestation-check.json | `244a93ae374298fd70d887e4bd9d32992a73c79cf415ec896ebbe6886ac8acbe` |
| check-attestation.py | `aca030e935883216bfa3395135892ab3fe62053b3e34cdf110eb52d5452ab162` |

## Контрольные суммы прочитанных входов

SHA-256 фиксирует рабочие документы поверх указанной основы. После изменения
любого входа требуется сверка затронутых выводов; этот список не связывает
будущий PR с ещё не созданным SHA.

| Файл в F216 | SHA-256 |
|---|---|
| contracts/ci-release.md | `fdcfa9546b3820673be724e661b614f1a80b3d66080725a36b6686f6e89999bb` |
| contracts/dev-manifest.md | `7e9deafa98a77a570d40f954f969dea586a3954cc76e41f49c5a9054bce46fed` |
| contracts/feature-claim.md | `df768690683494fc4e4956c3077a76cf6fd9d9bdf10bc3c353278d611b34e7e0` |
| contracts/harness-package.md | `ae363c77022516739a6da68f02ab636243887205243c9110a02063d6670b559a` |
| contracts/legacy-impact.md | `1b8784eddbe89e4b86a8af532d681b48cd5bcf06d8e48c2b13287f06aee8587c` |
| data-model.md | `7d46a7547abd607d456ffc67d1eb7a42494c03eec03a6bbf84780a43088b0b14` |
| plan.md | `adeb060ed0995bd522c49c5616e80a8b4f40526ab52b0e803cba3adf8c43e4d6` |
| quickstart.md | `079544c3a531917b6fc239568571e506b415d0aa98fc6ccede1e2e76cacf0dfb` |
| research.md | `53511648e30180427c317718849e586c971f10321fd35d47bd1255a98e6ce452` |
| spec.md | `f3df0cdd97df83c40ef8e9b3e09569061250a218950d347f43d0a7bd5075de0a` |
| tasks.md | `aa07a9dd45dfd4c609d1f5293471ded71ba850056f04c4da6d89e040e2f81ffb` |
| reconciliation-20261026.md | `5a7b6697561a12d94b13facec767860a9165a8edeeaf5e5a897e8f8c10a3e57a` |
| changes/unreleased/F216.yaml (от корня репозитория) | `01b0ea80b869db884c3b4db1eaeb9df638feb4cf536ff41b0204f285458146af` |


## Повторная проверка принятых преемников F229/F249

Основа чтения: `6f5ac8f9e74f158584835ff32304f84ad2094121`, чистая рабочая
копия перед изменением reviewer-owned файлов. Это дополнение уточняет прежний
результат 16/23: теперь **18/23**, открыты **G5/G8/G17/G18/G23**. Требования
сохраняют **16/16**. Решение всей F216 остаётся **BLOCK**.

Повторного запуска Dev, приложения, тестов, сборки, CI или публикации не было.
GitHub API в этом проходе не вызывался. Независимо прочитаны полные сохранённые
комментарии и документы преемников:

- [F229: окончательная проверка перед merge](https://github.com/yshishenya/graf/issues/6276#issuecomment-5514328306):
  02.09.2026, PR #6413, head `4d9d579c65e8c44f911bc37a0d9220547c0cc717`,
  controlled failure/compensation, explicit rollback и final promotion13/13;
  все девять реальных image IDs соответствовали manifests. Финальный
  `dev-4d9d579c65e8` собран/promoted после rebase, exact SHA подтверждён.
  Более ранняя проблема mutable image не игнорируется: этот комментарий
  фиксирует исправленную проверку, а не прежний недействительный rehearsal.
- [F229: принятое закрытие](https://github.com/yshishenya/graf/issues/6276#issuecomment-5541569686):
  04.09.2026, PR #6499, Candidate SHA
  `704a374f0eee454fa41e7bd820154c900cd0e910`, release-full33869861986,
  v2026.09.04.1. Прямые tag object и русский текст Release в предоставленном
  наборе отсутствуют: G17 остаётся открытым.
- [F249: принятое закрытие T038](https://github.com/yshishenya/graf/issues/6786#issuecomment-5586487199):
  08.09.2026, PR #6792; первоначальная реализация #6707, интеграция #6790.
  Изолированный холодный restore27,43с, реальная компенсация
  `aa031ac95bb247bd17e5d9ddf20e4ec0f5025a51` к
  `f1a21658405bd2f681363f0f8d998caa63ca4206`, затем принятый переход
  `b0fd763e870533ad5609e45289fcc4e04a6a9391`. Общий итоговый
  `dev-e81b412dff92` соответствует Candidate SHA
  `e81b412dff920cc29ed37de60be13dd8fc4d1c43` и smoke13/13.
- `specs/249-notification-control-design/implementation-evidence.md:478–498`
  прямо подтверждает компенсацию, schema0086→0088 и сохранность digest.
  Раздел :518–531 прямо подтверждает установленный проход на
  `6fefaeb5b68adcd4fd30ca0d5f447b9114891398` с сохранением bundle ID,
  подписи, designated requirement, entitlements и разрешений, затем
  контрольное открытие на `14ff8188a032c78b14d9ea01515f547cef2ea8f8`.
- `specs/229-dev-runtime-full-stack/live-validation.md` прочитан целиком.
  Последний раздел сам требует следующую проверку; его незавершённый
  результат не выдан за окончательную приёмку. Принятые последующие
  результаты взяты из названных сохранённых комментариев.
- `specs/249-notification-control-design/checklists/dev-schema.md` и
  `review-evidence.md` различают принятие требований и установленную
  приёмку; одно не подменяет другое.

Остаток не требует повторять уже принятые сценарии: G5 — подтвердить область
ownership; G8 — полноту безопасного набора внешних доказательств; G17 —
достать сохранённые tag/Release; G18 — достать полную запись пропущенных
проверок; G23 — проверить полный gate внешней публикации и происхождения.
Сведения сентября подтверждают историческую приёмку, а не текущее состояние
приложения, стенда или разрешений 26.10.2026. Доказательства сохранности
содержат только digest/числа/SHA; частные данные reviewer не открывал.

Прочитанные сохранённые входы этого дополнения:

| Вход | SHA-256 |
|---|---|
| specs/229-dev-runtime-full-stack/live-validation.md | `02b100a63287575ee3e0b2bf96e66cc624045025e0f2b104e3513e78b6001379` |
| specs/249-notification-control-design/implementation-evidence.md | `a176f84e9ac1a7b57a64de8f1f2523898f570379c56dc508dad7d0709c0267cc` |
| specs/249-notification-control-design/checklists/dev-schema.md | `e0e281efb925b250cbc4b859d28b4a2012eecbc4e78e1b9f16a36bb33415f80c` |
| specs/249-notification-control-design/review-evidence.md | `bc54966a2056f6cfd1588718866f961f6df46ac5fd59ec7395929ff3c7aa3b8f` |
| f229-issues-readonly.json | `f2de44eec9c03bb722dab8aa20d8b73ebf8dd872b1677766514e2891dfd13c92` |
| f249-issues-readonly.json | `2e7e5b6925afec05b34b3ddf4462d7f073876f19c589399d071b79acf9a6859a` |


## Дополнительная узкая проверка G17

После предыдущего результата 18/23 исполнитель предоставил три прямых
сохранённых ответа GitHub; reviewer самостоятельно API не вызывал.
Прочитан весь русский текст опубликованного выпуска и оба объекта tag.

- Release `382716588`: `tag_name=v2026.09.04.1`,
  `draft=false`, `prerelease=false`, `published_at=2026-09-04T12:51:34Z`.
  Заголовок «v2026.09.04.1 - обновление GRAF» и body на русском содержат
  изменения, совместимость, ограничения, описание проверки и ссылку #6415.
- `refs/tags/v2026.09.04.1` указывает на annotated tag object
  `d40fd94cf943c7eb8ba4b66809031a3e89ca328b`; его `object.type=commit`,
  `object.sha=704a374f0eee454fa41e7bd820154c900cd0e910`.
- Commit и URL выпуска совпали с принятым закрытием F229/#6276,
  [комментарий 5541569686](https://github.com/yshishenya/graf/issues/6276#issuecomment-5541569686).
  Поле Release `target_commitish=master` не использовано для определения SHA:
  точный SHA получен по цепочке ref → annotated tag → commit.

Это достаточное доказательство точного критерия G17; он отмечен выполненным.
Предыдущие записи об отсутствии прямого tag/Release сохраняют историю
проверки, но их открытый вывод G17 заменён этим дополнением и строкой таблицы.
Новая публикация, установка или проверка текущего стенда не выполнялась.
G18 без полной записи пропусков остаётся открытым.

Итог после повторного чтения обоих checklist: требования **16 checked / 0
unchecked**; governance предметно **19 checked / 4 unchecked**, всего
**20 checked / 6 unchecked** с тремя альтернативами решения. Открыты
**G5/G8/G18/G23**. Решение **BLOCK** сохранено; полная F216 не принята.

| Прочитанный дополнительный вход | SHA-256 |
|---|---|
| f229-release-v2026.09.04.1.json | `407cefd508b918509db8f4a8b1e9309258b6355a533d9aa30fa85678fa7bc0d7` |
| f229-tag-v2026.09.04.1.json | `fb517f820ccdf59caf4a51f1914535fd46b17a2f020f5048f6dac39b0750302a` |
| f229-tag-object-v2026.09.04.1.json | `8ea57350cf180d9e62e86fad6af8c07c1d9ab5232d275f15d940df67f4b7952c` |
