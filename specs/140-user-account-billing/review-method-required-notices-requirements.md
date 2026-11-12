# Независимое ревью требований MRC — 12.11.2026

**Результат: PASS качества требований, checked 14 / unchecked 0.**

Исполнитель: `/root/f140_mrc_requirements_review`, диалог
`01a140f0-8073-7de0-bc68-03d1ac57ff06`. Область — FR-110/MRC1–MRC6,
F140 T068/T070, #4922/#4926, lane **high-risk-product**. Проверял достаточность,
ясность, измеримость и согласованность требований до реализации.

Рабочая копия `/private/tmp/graf-f140-method-required-20261112`, ветка
`codex/140-method-required-notices`, исходный HEAD
`c8de0b01ca5de106694186aac48efd34b8f61b4b`. Авторские проектные изменения
ещё не закоммичены; их проверенные байты определены SHA-256 ниже, а не одним
HEAD. `.specify/feature.json` и штатный `check-prerequisites.sh --json --paths-only`
указывают на `specs/140-user-account-billing`; задача не выведена из имени
физической рабочей папки.

## Основания каждого пункта

Пути без префикса в таблице относятся к `specs/140-user-account-billing/`.
`F278 spec.md` означает `specs/278-production-billing/spec.md`,
`constitution.md` — `.specify/memory/constitution.md`. Все эти источники
прочитаны самостоятельно; их суммы и карта применимости приведены ниже.

| Пункт | Результат и исходные строки | Почему требований достаточно |
| --- | --- | --- |
| CHK001 | PASS — spec.md:1421–1425; research.md:3–16; data-model.md:14–19 | Отдельно заданы общая ошибка проверки, пригодность метода и неизвестный исход. manual_resolution не становится отсутствием метода; отсутствие provider_id не означает отсутствие отправки. |
| CHK002 | PASS — data-model.md:9–19; spec.md:1426–1432,1443–1448; quickstart.md:33–37 | Точный workspace/kind=renewal/UTC paid_through; без срока нет выборки. Таблица различает canceled/succeeded, unsent scheduled, scheduled с ID и остальные незавершённые состояния. |
| CHK003 | PASS — spec.md:771,1426–1437; plan.md:106–125; contracts/notifications-support.md:5–24 | Приоритет результата периода задан и для planner, и для обеих страниц, включая старый method_required, recurring-off и method/price/receipt/temporary blockers. |
| CHK004 | PASS — spec.md:1433–1437; contracts/notifications-support.md:8–24; plan.md:120–125 | Есть согласованные текст, баннер, action path и result=method_required; скрыты primary actions новой оплаты/early payment/resume, доступны история/помощь/cancel. Нейтральная навигация к методу не объявляется решением старого платежа. |
| CHK005 | PASS — spec.md:55–72,762–785,1438–1448; F278 spec.md:168–175,202; plan.md:106–113 | MRC сохраняет три окна, запрет новой отправки при неизвестности, cutoff/Free, отказ от будущего списания и однократный поздний успех. Историческая одна попытка явно заменена текущим правилом F278. |
| CHK006 | PASS — spec.md:1443–1448; data-model.md:21–28; plan.md:111–113; quickstart.md:12–19,33–37 | Названы неизменные сумма/валюта/снимок/срок/grants/method/key/authority/version/прежние audit rows и ограниченные state/status/resolution/прежний audit перехода; повтор не создаёт второй POST/операцию/аудит отправки. |
| CHK007 | PASS — spec.md:819–823,1432,1452–1454; plan.md:97–119,130–136; data-model.md:9–12,21–28; contracts/security-privacy-compliance.md:3–17; quickstart.md:8–10,33–37 | Owner/CSRF/RLS и tenant boundaries наследуются без ослабления; planner использует прежний workspace lock/FOR UPDATE, UI читает без записи. SQL/read error не превращается в пустую историю; новые сеть/сущности/секреты не вводятся. |
| CHK008 | PASS — spec.md:130–136,1416–1419,1458–1462; research.md:17–28; contracts/notifications-support.md:26–32; quickstart.md:48–53 | Новый method_required producer, saved_method_missing→attempt_failed, прочие семейства T068/T070, SSN, реальная доставка #7524, выпуск и развёртывание явно отделены. |
| CHK009 | PASS — spec.md:1449–1456; quickstart.md:12–19,48–53 | Проверка требует настоящих planner/charge и сохранения PostgreSQL, commit/новых AsyncSession, ошибок до POST и после одного synthetic POST, точных счётчиков 0/1 и причинного отказа старого handler. TypeError задан отдельно. |
| CHK010 | PASS — quickstart.md:20–25,33–37; plan.md:106–110; data-model.md:9–27 | Требуется матрица manual_resolution/unknown/sent со старым method_required и method/price/catalog/receipt, новое окно без новой операции, rollback, другой период, finished/unsent и сохранение трёх окон. |
| CHK011 | PASS — quickstart.md:26–37,48–53; spec.md:1426–1437,1449–1456; plan.md:120–125 | Обе настоящие page handlers читают сохранённые PG строки; заданы post-POST manual_resolution без ID, старое состояние, каждый blocker, recurring true/false и result=method_required. Jinja assertions прямо отделены от продуктовой приёмки. |
| CHK012 | PASS — spec.md:829–834,1454–1456; contracts/notifications-support.md:31–32; quickstart.md:48–53; plan.md:130–136 | Требования к status semantics/WCAG2.2AA, обеим темам, клавиатуре, VoiceOver, 200%/360px и единственному свободному GRAF Dev сохранены. Непройденная ручная приёмка должна оставаться явно непройденной. |
| CHK013 | PASS — plan.md:102–119; data-model.md:9–23; quickstart.md:26–37 | Единый запрос/предикат, один прочитанный список на страницу, сохранение tuple(label,nominal_first)/строкового wrapper; storage preview/resume snapshot используют ту же классификацию, POST resume заново проверяет под lock. |
| CHK014 | PASS — spec.md:128–136,1458–1462; research.md:1–28; plan.md:93–136; constitution.md:345–403,456–530; tasks.md:211–228 | Clarify и Phase0 ограничивают решение уже действующей финансовой правдой; pre/post constitution описаны как design PASS. Независимый checklist, затем tasks/analyze/sync, точные SHA/base/CI и отдельные runtime/release gates не ослаблены; исходные задачи остаются открытыми. |

## Замечания и последующие ворота

Неразрешённых замечаний к качеству требований в ограниченной области MRC:
**CRITICAL 0 · HIGH 0 · MEDIUM 0**. Дополнительное решение владельца о деньгах,
согласии, сроках хранения или доставке для этого предварительного исправления
не требуется: эти правила не меняются. Это не принятие SSN-политики и не
принятие ещё не спроектированного источника method_required.

Отсутствие MRC-декомпозиции в текущем `tasks.md` не выдано за завершённую
плановую работу и не является дефектом порядка этого review: план явно требует
сначала независимый допуск требований, затем tasks → analyze → sync уже
существующих #4922/#4926. Реализация допускается только после этих остальных
ворот; настоящий отчёт сам по себе их не проходит. Старое общее checklist
фичи не использовалось как готовый PASS MRC.

Проверку исполнения причинного RED/GREEN, настоящей PostgreSQL/AsyncSession,
RLS/ролей, обоих page handlers и всех потребителей проекции ещё должен
выполнить автор в рамках следующего назначения. Этот reviewer не запускал
тестов, БД, приложения, provider API или почту. Ранее сохранённая диагностика
прочитана как основание исследования, а не как мой запуск, PostgreSQL-проверка
или новая фактическая приёмка.

GRAF Dev, темы, клавиатура, VoiceOver, 200%/360px, CI точного SHA/актуальной
основы, независимое ревью кода/сходимость, выпуск/развёртывание и реальное
получение #7524 сохраняют отдельные ворота. Исходные T068/T070 и их issues
не завершены этим PASS. #7899 остаётся последней по собственным условиям.

## Собственное чтение и происхождение

Квитанция собственного первого полного чтения:
`/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/f140-mrc-reviewer-reading-20261112.json`.
Она содержит исполнителя/диалог, неусечённые output refs, число строк,
SHA-256 каждого документа и восстановленные после сжатия целые применимые
оригинальные разделы. Чтение другого агента не использовалось вместо своего.
Перед изменением checklist все суммы полных чтений повторно совпали.
Хеш подтверждает байты, но не заменяет чтение или продуктовую приёмку.

| Прочитанный документ | SHA-256 проверенных байтов |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5c3ab1f885dbf324edab70c0f4b7a5451208b3d7307c1ca7a5afdd7af0c8eb22` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/development-process.md` | `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `ac6cb05dc7a60b2c18cc21694b9ac052b4a0a60d91fb1527084e46f71e83bae2` |
| `specs/140-user-account-billing/spec.md` | `1ce36bdd7002de0505246400f876dd32f32d17965d1cf4c4246444cb2be2fc70` |
| `specs/140-user-account-billing/plan.md` | `48ab44e598e6bdbaa678090e4245e3c8e3b45aab71e504962c3f5c01fdca76a1` |
| `specs/140-user-account-billing/tasks.md` | `f95cfb943afe3e4e70ac147ada6b176ad1ab8e7ce37474e9823cadc5b8a34049` |
| `specs/140-user-account-billing/quickstart.md` | `9071f96df887168eb1cc6c362588b99f7cc87ca594fb46613a81193497efa8de` |
| `specs/140-user-account-billing/research.md` | `2cd75fb8fdd804a85cff239efa687bcbb778040ddb2c4e465caa8c0d6298fa86` |
| `specs/140-user-account-billing/data-model.md` | `4d902504a38510c526a2042a4ee90533e93079057888fbbe90e753180fdd664f` |
| `specs/140-user-account-billing/contracts/notifications-support.md` | `5a0139475737c0b2fe278527682ffe87252566fc07adb45f9eb1c4f0174b3e8e` |
| `specs/140-user-account-billing/contracts/security-privacy-compliance.md` | `38934189b91e33a070b49e61673020d41530eec3d06a4fad5bd00f3317071cfc` |
| `specs/278-production-billing/spec.md` | `d452d625cf5035edcdd144c34561aeb2c5d1a19c29826c61505801a3dd53e09c` |
| `/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/f140-method-required-root-diagnosis-20261112.md` | `21d62a09da223b3dc57bba3bdace6d5941f83c0ab53af313376c15f1471ca063` |
| `specs/140-user-account-billing/checklists/method-required-notices.md` | `8e7728d856598b6e0782139ffc9d829956220513f38d45f939dcc0b26fe160c3` |

Сумма checklist в таблице обозначает входную версию с 14 незаполненными
пунктами; ниже итоговое чтение и счётчики относятся к изменённой версии.
Суммы итоговых checklist/отчёта передаются автору отдельно, чтобы отчёт
не содержал рекурсивный собственный хеш.

## Карта применимости и зависимостей

| Оригинальные разделы | Применимость |
| --- | --- |
| AGENTS.md и guidance README/document-reading; spec-kit-flow целиком; development-process целиком | Авторство и полномочия reviewer, границы записи, достаточность требований и следующие ворота. |
| Конституция II/IV/V/VI/VII, Product And Platform Constraints, Development Workflow And Quality Gates, Governance; product-gates целиком | Неослабление управления, жизненного цикла, независимого review, доступности, внешних границ, выпуска. Изменения принципов не нужны. |
| PRD §25–27, §29–30; текущий статус: начальная запись, Feature272, Feature140/199 | Приватность, аудит, tenant isolation, правдивое сообщение и доступность; текущие правила заменяют указанные исторические one-attempt/emergency/launch-registry утверждения. Остальные неизменные разделы также прочитаны полностью ранее в этом же диалоге. |
| F140 spec: Scope/Product Decisions, Session2026-11-12, US4/US5/US9, Checkout/Subscription/Invoices, Notifications/Security/Accessibility, MRC1–6 | Действующие роли, деньги/согласие, явный приоритет незавершённого результата, интерфейсные действия, безопасность и измеримая приёмка. |
| Plan: MRC, pre/post Constitution Check, Architecture/Validation, Phase0/1; research MRC; model MRC; quickstart MRC; оба контракта | Минимальный существующий механизм, locks/query/state, потребители проекции, причинные проверки, отдельные ручные и почтовые ворота. Все файлы прочитаны полностью. |
| Tasks US9/T068/T070, весь tasks.md | Сохранены исходный объём/открытость задач; следующий шаг tasks-stage ещё предстоит. |
| F278 spec целиком, особенно FR007–014/028/041 и уточнение T035 | Три окна, неизвестность/повтор, отзыв/поздний успех, отсутствие второго POST и разделение тестовой/живой приёмки. |
| Внешняя root-diagnosis от12.11 целиком | Историческая причинная диагностика и её пределы, включая отсутствие provider_id после синтетической отправки. Она не является выполнением будущей MRC-матрицы. |

Зависимых непрочитанных ограничений, необходимых для этого решения о
качестве требований, не осталось. Подробные процедуры local-development,
release-and-validation и billing-launch нужны исполнителям соответствующих
будущих действий: reviewer не выполнял сборку, запуск, установку, PR,
выпуск/развёртывание, живую оплату или closeout. Другие семьи уведомлений и
SSN не приняты через это ограниченное ревью.

## Контроль владения и итог

Reviewer изменил только `checklists/method-required-notices.md` и настоящий
отчёт в проекте, а также свою внешнюю квитанцию чтения. Авторские spec/plan/
research/model/quickstart/contracts/tasks и все code/test/governance-файлы
не изменены reviewer. Git/GitHub, commit/PR, release/deploy, Dev, provider,
данные и почта не менялись.

Итоговый checklist перечитан самостоятельно после записи: **14 checked,
0 unchecked**. Эти отметки означают достаточность требований MRC; фактическая
реализация и исходная приёмка остаются отдельной незавершённой работой.
