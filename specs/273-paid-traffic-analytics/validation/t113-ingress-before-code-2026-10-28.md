# Независимый допуск к ingress/delivery T113 — 28.10.2026

**Gate: PASS качества требований перед изолированной реализацией следующего уже запланированного среза T113. 117 checked / 0 unchecked. Critical=0 / High=0 / Medium=0; новых блокирующих уточнений не найдено.**

Проверяющий: `/root/activation_requirements_gate`. Основа: `ec196e9e2a7973eb3c1dfd3ecd34015e8d92abcc`, ветка `codex/273-activation-ledger`. Рабочая копия при начале проверки чистая. Активная фича подтверждена .specify/feature.json и check-prerequisites --json --paths-only: specs/273-paid-traffic-analytics. Lane: independent reviewer gate существующего high-risk Spec Kit среза. Назначение — оба HTTP ingress, server-auth, затем bounded maintenance delivery; T112 triggers отдельно.

## Метод и пределы

Все117 действующих вопросов четырёх reviewer-owned списков перечитаны непосредственно, их отметки не приняты за самостоятельное доказательство. Проверены неизменность принятого27.10 полного снимка требований/зависимостей и применимость его матрицы к текущему срезу. Самостоятельно целиком перечитан activation-milestones и короткий analyze, непосредственно перечитаны затронутые разделы plan §Продолжение T112/T113, data-model §Устойчивое решение, quickstart §Сценарии4/5, operations §Lifecycle T113/хранение/backup/readiness, spec §FR021–029/048–050/SC, tasks Phase13 и T106/T109–T111. Использовано прямое разрешение пользователя для F273: затронутые требования/зависимости перечитываются, остальной ранее прочитанный набор сверяется по SHA-256. Повторное полное чтение всего PRD/current-product-status здесь не заявляется; полная продуктовая/рабочая приёмка не входит в назначение. Хеш не назван доказательством выполнения продукта.

Все восемь принятых документов, четыре checklist, constitution/guidance, legal/attribution/anonymous зависимости и оба backup-скрипта совпали с контрольными суммами предыдущего независимого requirements-review. Изменения кода ledger после27.10 отдельно рассмотрены в t113-ledger-implementation-review-2026-10-28.md; кодовый PASS не используется вместо качества требований. В этом назначении код не меняется и кодовая приёмка не выполняется.

## Проверенные условия допуска

| Условие | Вывод и текущее основание |
| --- | --- |
| Порядок работ | PASS — plan/tasks прямо предусматривают ledger → оба ingress и server-auth → delivery/T106 → T112; нового проектирования или дублирующей задачи не требуется. |
| Владение аккаунтом | PASS — trusted AuthenticatedPrincipal либо завершённая server-auth; body pseudonym не выбирает владельца, несовпадение отвергается до записи. |
| Оба HTTP пути | PASS — /events и /posthog-desktop-capture используют одну admission boundary; прямая отправка first-события провайдеру в обход запрещена. |
| Совместимость desktop | PASS — форма запроса прежняя, новый клиент добавляет существующие auth headers; старый получает безопасный отказ аналитики без влияния на запись/вход. Нового login/секрета нет. |
| До авторизации | PASS — first_open без уже доверенного install key не создаёт account-веху, intent или внешний первый счёт. Произвольный client ID не признаётся ключом. |
| Точные триггеры | PASS — desktop account-connected только подтверждённый desktop путь; result/value требуют владельца, готовности и видимого открытия; T112 не заменяется GET/prefetch. Их отдельная реализация остаётся открытой. |
| Первое решение | PASS — одна relation, unique(account,event), проверенный snapshot≤16KiB, immutable исходные поля, две фиксированные provider states; атомарность и rollback определены. |
| Свежие ворота | PASS — основание уровня2, readiness/выключатели и отдельная рекламная цель проверяются перед admission и непосредственно перед каждым side effect; body/старый snapshot этого не заменяют; unknown запрещает запись/передачу. |
| Отзыв и локальная веха | PASS — отказ/отзыв цели отменяет её намерение; необязательный рекламный отзыв сам по себе не удаляет допустимую локальную веху. Утрата основания уровня2 включает ledger в удаление. |
| Право попытки | PASS — условный claim и attempt_id, commit до сети, отсутствие SQL-lock во время сети, finish только владельцем попытки; два работника не отправляют одновременно. |
| Исход доставки | PASS — HTTP2xx=submitted, только отдельный точный readback=confirmed; timeout/5xx/падение после начала транспорта=ambiguous без слепого retry. Только доказанный технический pre-send допускает retry. |
| Независимость получателей | PASS — два отдельных состояния; успех одного не повторяется вследствие сбоя другого; not_requested не превращается в скрытую отправку старых событий при включении. |
| Ограничение ресурсов | PASS — существующий maintenance worker, ≤20 строк/проход,1 запрос одновременно, timeout≤5с,пауза60с; продукт не ждёт сети, сбой не останавливает другие maintenance-задачи. Новый брокер/процесс не нужен. |
| Метаданные | PASS — существующий каталог/forbidden fields, внутренний closed source_kind, closed reason; private content/IP/auth/provider response не попадают в payload/отчёт. |
| Lifecycle и restore | PASS качества — until_decision/category/account cases, GRAF DB T110 отдельно от PostHog T118, quarantine и invalidation receipts, запрет admission отсутствующего account+event при unknown gap. Настоящий restore ещё нужен до включения. |

## Все117 пунктов

| Проверочный список | Проверено `[x]` | Открыто `[ ]` | Применимость |
| --- | ---: | ---: | --- |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | 16 | 0 | Все действующие вопросы сохраняют смысл принятого27.10 gate; новых категорий/целей/получателей/прав нет. |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | 45 | 0 | Все действующие вопросы сохраняют смысл принятого27.10 gate; новых категорий/целей/получателей/прав нет. |
| `specs/273-paid-traffic-analytics/checklists/security.md` | 27 | 0 | Все действующие вопросы сохраняют смысл принятого27.10 gate; новых категорий/целей/получателей/прав нет. |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | 29 | 0 | Все действующие вопросы сохраняют смысл принятого27.10 gate; новых категорий/целей/получателей/прав нет. |

Итого: **117/0**. Подробная117-пунктовая матрица оснований сохраняется в t113-requirements-review-2026-10-27.md; её требования и вопросы не изменились. Вновь проверена именно применимость каждого вопроса к продолжению T113, а не выполнение ещё не написанного ingress/dispatcher. Отметки checklist не изменялись: недостаточных вопросов для возврата в `[ ]` в текущем контракте не обнаружено.

Analyze27.10 самостоятельно перечитан. A1 (trusted/atomic/common boundary), A2 (technical retry vs withdrawal/unknown), A3 (absent-row restore gap), A4 (dependency/task order) остаются согласованными. Его восемь входов сохраняют точный digest `95663c306cd000b6e2c32f66e8588847f1e2c329c33d658c38300df0e5fe7fdf`; оснований аннулировать результат **0 critical / 0 high / 0 medium / 0 blocking_clarifications / 0 unresolved_duplications** для неизменного среза нет. Это revalidation применимости существующего analyze, не новый запуск команды speckit-analyze и не общий аудит всей F273.

## Что разрешает и чего не принимает этот gate

Можно продолжать изолированную реализацию авторизованной общей границы обоих ingress, server-auth и bounded worker в пределах принятого27.10 контракта. Существующую связь T112/T113/T106 с GitHub основной агент проверяет отдельно; этот read-only reviewer не проверяет/не меняет удалённый tracker. Новые цели или расширение сбора этим допуском не вводятся.

Реальные T098/retention/backup/restore/capacity/provider receipts не требуются как условие написания и проверки кода на изолированных данных. Они остаются обязательными перед рабочим включением writer/доставки. Реализация обязана сама отказать при неизвестных/неполных/устаревших доказательствах; gate не разрешает подставить тестовый receipt в рабочее состояние.

До завершения T113 остаются профильные auth/ownership/concurrency/DB failure/transport/fresh-withdrawal тесты, lifecycle/restore из прежнего code-review, converge, точные GitHub SHA/base проверки, общий кандидат, выпуск и операторская приёмка. Триггеры T112, отдельный readback confirmed, рабочие основания и коммерческие результаты не принимаются этим отчётом. Счёт локальных тестов и checklist не является трафиком, регистрацией или продажей.

## SHA-256 текущих входов

- `specs/273-paid-traffic-analytics/spec.md` — `0058816587634dc8235c0d2fa44a02218a5978488e37d001a0c909342401155d`
- `specs/273-paid-traffic-analytics/plan.md` — `86991b85ebeed9a9c3d7d2d50a980b4eb827796734fa0b4bd6df7f92c08e79ec`
- `specs/273-paid-traffic-analytics/tasks.md` — `f5fe73b9847ac10d05029af9ed93ef939e119cf46e4b1cdd8c1cbdcf6fe48787`
- `specs/273-paid-traffic-analytics/research.md` — `a9b5331c68424cd86f47119b8994db442da4250cc536683695d9488fe9b6f46b`
- `specs/273-paid-traffic-analytics/data-model.md` — `52fb96e3dd9c399c741a9c982916fd755a056580efdd36539bfc7f1a91cc74be`
- `specs/273-paid-traffic-analytics/quickstart.md` — `c8fdc2c68ffc8e3aa86ed32b250603022e643df4e4f3ede3091a073fe1b05479`
- `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` — `2bba8a3fa0a7040591664343158e4d0b3b1045cfe356a96e3e30e2f93fa4adc5`
- `specs/273-paid-traffic-analytics/contracts/operations.md` — `f696f7b87024783dad0a28ab84af0c7b3dc2329a595eb470c256232a3797c0fb`
- `.specify/memory/constitution.md` — `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`
- `docs/agent-guidance/README.md` — `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb`
- `docs/agent-guidance/product-gates.md` — `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`
- `docs/agent-guidance/document-reading.md` — `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411`
- `docs/agent-guidance/spec-kit-flow.md` — `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`
- `docs/agent-guidance/development-process.md` — `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864`
- `specs/273-paid-traffic-analytics/legal-basis.md` — `f5c8b5ea1bb2a145f438069dc64b0e3816fb46496de86aecd17d02d47db3d423`
- `specs/273-paid-traffic-analytics/contracts/attribution-handoff.md` — `8d5808a1bd4a1bbc6fbdbbc8cf1d301e246dd8822c25e841bef7ceaca723fd82`
- `specs/273-paid-traffic-analytics/contracts/anonymous-aggregate.md` — `7e10a25d64c9d94951bec8440c1c84d205e5bfc0e87f31364f0739c5357ca47f`
- `infra/scripts/backup-rec-stack.sh` — `64c20e804b6dec0e73dd3c28778c81a9d076b3ddea5190ad4fb41961a40c20fc`
- `infra/scripts/rehearse-rec-restore.sh` — `fd442e9e76030bcc73244a706b36cc8ddf996e122f8f1d330431416dd62850ac`
- `specs/273-paid-traffic-analytics/checklists/requirements.md` — `b10a19943d788e9b8f5b3c9e322f6a614eb60f1cb8ea6cb207404bf82c3f3c30`
- `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` — `42f018d295b3c7fe50873612eeff9ec94c71a8d8b810060edb78a59ed7800b38`
- `specs/273-paid-traffic-analytics/checklists/security.md` — `d9c8078134a53d3a89c1171826a24b3271488fc2ff48687ad6a8bbf95eaf6678`
- `specs/273-paid-traffic-analytics/checklists/infra.md` — `ea43c13bb2ed6acba078bb6b511bcd6b981ac5db03d652548948b346ecfda87e`
- `specs/273-paid-traffic-analytics/validation/t113-requirements-review-2026-10-27.md` — `3286a8014b3b36a7825de3a308b566d2ae746688a62c1555cd724b0996e67655`
- `specs/273-paid-traffic-analytics/validation/t113-analysis-2026-10-27.md` — `0dec601b9e919ba582a61539125e14fa2b199fdceeb74307487fd19dbac90690`

До и после записи отчёта входы повторно сверены и совпали. После записи перечитаны все checkbox строки и итоги16/45/27/29;117 checked/0 unchecked. Проверяющий изменил только этот новый отчёт; четыре checklist сохранены без изменений. git diff --check выполнен. Код/тесты/spec/plan/tasks/Git/GitHub/релиз/рабочие данные не менялись; тесты, внешние запросы и доставка не выполнялись.
