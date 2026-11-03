# Независимое ревью проекта первой части T075 — 2026-10-30

**Решение: scoped PASS для требований операторского импорта B1–B3.**

Основа `847ccc82e7b2180a8c38f8769bc67ff39a342c8b`, ветка
`codex/140-registry-runtime`, плюс проверенные незакоммиченные документы.
Полоса: существующий Active Spec Kit slice с воротами высокого риска для
PostgreSQL, полномочий и финансовых данных; данное ревью меняет только документы
reviewer-а. Это разрешение продолжить проектирование/реализацию ограниченной
части после остальных ворот анализа, а не приёмка кода или денежных операций.

## Граница решения

Рассмотрен первый increment: официальный CSV → проверка → сохранённые
ограниченные метаданные/completeness/owned gaps → отдельный status после restart.
`files_complete` не является финансовой сверкой; `financial_status=not_checked`
обязателен до отдельного сравнения CSV/authenticated API/ledger. Вся T075 и
#4930 остаются OPEN. Не принимаются test-shop, real-shop, включение оплаты,
выпуск, deployment, другие задачи F140 и общие условия публичного запуска.

Старый `t075-requirements-review-20261030.md` сохранён без изменений. Его B1–B3
перепроверены относительно нового `contracts/registry-operator-import.md`.
Исторические X4–X7 не объявлены устранёнными во всей F140: явная precedence в
spec/plan/research/operations запрещает возвращать F199/F272/F278 и заменять
конституцию старым brand-distance. Это достаточно для отсутствия противоречий
в ограниченном импорте; глобальная сверка старых артефактов остаётся отдельно.

## Проверенные требования первой части

Ниже отметки относятся к качеству требований до реализации, а не к выполненным
тестам. Все десять требований подтверждены текущими документами.

- [x] IMP001 B1: один внутренний server CLI, dry-run по умолчанию, явный execute;
  отсутствуют browser/desktop/public API и новая служба.
- [x] IMP002 B1: роль определяется реальными session_user/current_user,
  row_security, rolsuper/rolbypassrls и точными operation/feature area; URL и
  SET ROLE не считаются полномочием. Это совпадает с существующим
  `billing/database.py`, включая `rec_maintenance_allowed()`.
- [x] IMP003 B1: две shop-level таблицы имеют ENABLE/FORCE RLS и узкие права;
  существующий workspace audit не ослабляется, финансовые права tenant не
  расширяются. Проверки фактических ролей/контекстов входят в будущую приёмку.
- [x] IMP004 B2: один официальный русский профиль, явная UTF-8 граница GRAF,
  строгая ширина/заголовки, обязательные идентификаторы/сумма/RUB/время и
  проверяемые имя/шапка/дата. Не выдумываются обязательные row shop/env поля;
  отсутствующая подпись CSV и доверие операторскому источнику названы честно.
- [x] IMP005 B2: раздельные payments/refunds, уникальность identity по всем
  частям, последовательность/last, declared empty versus missing, лимиты
  чтения и отказ при неподдерживаемом входе заданы однозначно.
- [x] IMP006 B2: footer проверяет count и gross операций, включая имеющиеся
  count/gross по типам payments с обязательным `Тип платежа`; комиссии,
  НДС, net и обеспечение не превращают импорт в бухгалтерский движок.
- [x] IMP007 B3: стабильные versioned config/input hashes включают все
  влияющие на валидацию правила, scope, kind/index/last/empty и реальные
  byte hashes. Порядок argv, пути, owner/operator не влияют; одинаковые байты
  разных частей не схлопываются в одну часть.
- [x] IMP008 B3: общий по магазину/окружению/дню транзакционный lock,
  неизменяемые receipts, replay, optimistic replacement текущего digest и
  атомарные gap transitions исключают потерю последнего принятого набора.
- [x] IMP009 B3: ошибки/DB outage не объявляются успехом, owner/deadline не
  продлеваются повтором, исправление имеет closing receipt/actor/reason/time,
  закрытые поколения gap не переписываются; status не требует CSV после restart.
- [x] IMP010 B1–B3: запрещены raw CSV/пути/provider IDs/деньги/контакты в
  общем store/выводе; исходный экспорт не копируется и не удаляется. Импорт
  не меняет provider state, entitlement, invoices или recurring consent.

**Предметный итог: 10 отмечены / 0 открыты; B1 PASS, B2 PASS, B3 PASS.**

## Обнаруженные и устранённые неоднозначности этого ревью

При первом чтении контракт говорил о «денежных итогах» footer без различения
полной суммы операции и комиссии/НДС/net. Также не был явно определён
семантический состав config/input hashes. Эти два небольших замечания переданы
владельцу исходных требований; я сам контракт не редактировал.

В текущих байтах проверены внесённые уточнения: gross/count и per-type payments;
комиссии/НДС/net/обеспечение не принимаются финансово; versioned fingerprint
содержит все правила и пределы; канонический отсортированный digest содержит
scope/config/expected-empty kinds и kind/index/last/empty/actual-byte-hash,
single=index1/last=true. Замечания закрыты на уровне дизайна. Новых блокеров
ограниченного import-increment не осталось.

## Проверенные источники и пределы доказательств

Прочитан фактический diff семи исходных документов и весь новый контракт,
перечитаны затронутые исходные разделы, правила reviewer/checklist gate,
контекст активной фичи и все восемь списков целиком. Хеши неизменённых
обязательных документов и прежних контрактов сверены с предыдущим отчётом;
новые scoped-уточнения не выданы за полное повторное ревью других подсистем.

Независимо прочитан `billing/database.py`: он действительно проверяет реальную
роль PostgreSQL, row protection и точный контекст. Проверен существующий
transaction advisory lock pattern в `billing/storage.py`. Существующий
`BillingAuditEvent.workspace_id NOT NULL` остаётся границей отдельного аудита.

Официальная страница
https://yookassa.ru/docs/support/merchant/payments/reports/reports-new
дополнительно прочитана точечно: отдельные имена файлов, multipart/10 000,
поля идентификаторов, точный формат суммы, Время платежа как подтверждение,
Время возврата как создание. Она не подтверждает универсальную кодировку
или подлинность/окружение каждого CSV. Это проверка опубликованного формата,
а не работающего экспорта конкретного магазина.

Приложение, тесты, БД, builds, release и реальные платежи не запускались.
Реальные grants/RLS, CLI/runtime/parser, ограничения ввода, restart/concurrency,
rollback и redaction ещё должны быть проверены по quickstart после реализации.
Синтетические старые пробы не превращены в успешную приёмку нового кода.

## Применимость и итоги восьми общих checklist

Все 220 исходных пунктов перечитаны, их исходная область не сужена переписыванием
формулировки. Глобальные отметки сохранены: ограниченный import PASS не доказывает
весь journey или запуск продукта. Для каждого списка ниже названа применимая
часть. Остальные его пункты находятся вне текущего изменения; прежние отметки
и причины открытости остаются историей общего ревью. В частности, незавершённая
финансовая сверка сохраняет общие reconciliation-пункты открытыми, а X4–X7,
product-market и launch gates не принимаются заново.

### `requirements.md`

К текущему импорту применимы CHK002/CHK012 (B1), CHK014 (только часть B2), CHK009 (восстановление B3) и общие запреты приватных данных. B1–B3 определены новым контрактом. Полный reconciliation/launch и X4–X7 этими выводами не принимаются.

Итог исходных пунктов: **16 отмечены / 9 открыты**. Открыты: CHK002, CHK012, CHK013, CHK014, CHK017, CHK018, CHK019, CHK023, CHK025.

### `payments.md`

К текущему импорту применимы разделение authority CHK001, идемпотентность CHK003 и только файловая часть CHK009. Команда не проводит деньги и не выдаёт entitlement. Whole-payment/renewal/refund/canary критерии не переоценены; финансовый результат остаётся not_checked.

Итог исходных пунктов: **14 отмечены / 6 открыты**. Открыты: CHK006, CHK009, CHK011, CHK014, CHK017, CHK020.

### `operations.md`

CHK001/CHK002 проверены в узкой части: ввод обоих видов, completeness, сохраняемый результат и поколение расхождения. Полная сверка API/ledger, общая система incidents, monitoring и canary не входят. Упрощённый detected/resolved путь не отменяет общий процесс инцидентов.

Итог исходных пунктов: **10 отмечены / 8 открыты**. Открыты: CHK001, CHK002, CHK003, CHK008, CHK011, CHK013, CHK015, CHK017.

### `security.md`

CHK001/CHK002/CHK006/CHK007/CHK009/CHK011 применены к реальной роли БД, двум отдельным таблицам, RLS inventory и безопасным метаданным. Доказано качество требований; действительные права PostgreSQL ещё предстоит испытать. Глобальные correction/four-eyes/refund требования и X4–X7 не закрыты.

Итог исходных пунктов: **11 отмечены / 6 открыты**. Открыты: CHK001, CHK002, CHK009, CHK012, CHK016, CHK017.

### `launch-readiness.md`

В пределах CHK005/CHK007/CHK008/CHK039/CHK040 проверены требования новых таблиц, восстановления, сроков и приватности импорта. Это не готовность магазина или публичного запуска. Все внешние согласования и финансовая приёмка сохраняются.

Итог исходных пунктов: **32 отмечены / 8 открыты**. Открыты: CHK005, CHK007, CHK017, CHK018, CHK021, CHK022, CHK033, CHK040.

### `post-plan-readiness.md`

CHK027/CHK031/CHK036/CHK038 проверены только для первого import-increment: файловая полнота, повтор/замена, DB outage/rollback, доступ и безопасный вывод. Полный journey CSV/API/ledger остаётся незавершённым. Старые общие X4–X7 и остальные подсистемы не приняты заново.

Итог исходных пунктов: **24 отмечены / 16 открыты**. Открыты: CHK003, CHK008, CHK010, CHK013, CHK015, CHK016, CHK021, CHK023, CHK026, CHK027, CHK031, CHK034, CHK036, CHK037, CHK038, CHK040.

### `product-market-2026.md`

Проверены применимые границы CHK019/CHK027/CHK033/CHK034/CHK038/CHK039: нет новой продуктовой refund-функции, доступа tenant к магазину, приватного evidence или заявления о запуске. Сегмент/WTP/COGS и прежние открытые пункты не имеют нового evidence и остаются открытыми.

Итог исходных пунктов: **35 отмечены / 5 открыты**. Открыты: CHK001, CHK004, CHK008, CHK009, CHK019.

### `ux.md`

Нового пользовательского экрана или маршрута нет. Применимы browser/desktop boundary CHK006 и требование правдивого результата CHK004: CLI отличает последнюю попытку, последний принятый набор и открытые gaps. UI/refund/renewal/reference-fidelity критерии вне этого increment не принимаются заново.

Итог исходных пунктов: **16 отмечены / 4 открыты**. Открыты: CHK009, CHK013, CHK016, CHK020.

**Всего исходных checklist: 158 отмечены / 62 открыты; отдельный scoped design gate: 10/0.**

## Простота решения и дальнейшие ворота

Один CLI в существующем Python package, stdlib CSV/hash/JSON и текущий
SQLAlchemy/PostgreSQL достаточны. Две небольшие таблицы обоснованы различием
неизменяемого receipt и изменяемого поколения gap; отдельный общий сервис,
интерфейс, SDK, dependencies, SFTP или бухгалтерский engine не нужны.

Перед кодом остаются штатные независимые от этого отчёта analyze/issue gates.
После кода нужны приёмка quickstart в изолированной PostgreSQL, convergence,
обязательные проверки точного PR SHA и основы. Ни scoped PASS требований,
ни files_complete не дают основания отметить всю T075 выполненной или закрыть
#4930. Уточнения дальнейшей financial reconciliation должны быть проверены
отдельно до её реализации/приёмки, без подмены provider time локальным временем.

## Контрольные суммы прочитанных требований и исходников

Хеши фиксируют проверенный незакоммиченный дизайн поверх указанного HEAD.
Старый отчёт и все исходные документы не менялись reviewer-ом. Контрольная
сумма нового отчёта передаётся отдельно, без самоссылки.

| Путь | SHA256 |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `specs/140-user-account-billing/spec.md` | `964fa33382fa5f04940349f7e27eb1e1aab9b453397a568985f1b0d5f79f9a88` |
| `specs/140-user-account-billing/plan.md` | `5a78f4a17c78ae60922cddfe9804a5b285f30f60428bc21b6094397347f0882c` |
| `specs/140-user-account-billing/tasks.md` | `2cdccb7df2c8d0686be3dc83a21c8d1ea3c93be4899f40563101fbfce6214599` |
| `specs/140-user-account-billing/quickstart.md` | `f1b1c37dc92dc91c373cc461e9d9c7e41944ffbd049eac4a1d362ae3080778e7` |
| `specs/140-user-account-billing/research.md` | `c52b9e95a4a2bcd926b1242e7aa1adba850097380b2c6a50a32f1d6fe12a49cc` |
| `specs/140-user-account-billing/data-model.md` | `cfc590a2085c40d925421f86055a2e6779c365e3c6bcb1c633d0eaed3c354e21` |
| `specs/140-user-account-billing/analysis.md` | `6c643edb08246d749afaf0402903ff924ebce5aeef647929576ac97ac9890534` |
| `specs/140-user-account-billing/t075-requirements-review-20261030.md` | `aca2cec1dc5ec1cc9d9b96a68f221a81723231a78a76b4efbf6fc9af489fcdc9` |
| `specs/140-user-account-billing/contracts/account-ia-ux-ui-cx.md` | `d25d152f2dadc8a8ececaa8e3771ad7d8017b9553799bfcae469db611cf716a4` |
| `specs/140-user-account-billing/contracts/billing-lifecycle.md` | `1d3e8fe3a672a34a4bc7a34bb6135800781d840e6e9350e0659bd142c5931ff7` |
| `specs/140-user-account-billing/contracts/entitlement-degradation.md` | `5aa1ea33309ca3641c32e8c9ab08ace8df61459a24c559a9262d9f1ae62e8809` |
| `specs/140-user-account-billing/contracts/http-interface.md` | `3b29db361d303f4cce4b8a9d64909449e527838fce9c953c4e9f2c441a52aeaf` |
| `specs/140-user-account-billing/contracts/notifications-support.md` | `3b5d29fc37d63087a70d05151da42f7bbe873276c98234a77e9826bba0fdac97` |
| `specs/140-user-account-billing/contracts/operations-reconciliation.md` | `a3a1917b91e0370b0ef477519509c0333ec8701aa4ae7803ed6685022c7a1cba` |
| `specs/140-user-account-billing/contracts/product-metrics.md` | `5c9d40022188d6de3a7fc2a9a3cf8bba737a031c5b80dc96f035232a022e62c1` |
| `specs/140-user-account-billing/contracts/registry-operator-import.md` | `297bfe6c3acb063d70a6ef634c287a901fc9c342549270eaeec2c15a35c5b0a5` |
| `specs/140-user-account-billing/contracts/security-privacy-compliance.md` | `38934189b91e33a070b49e61673020d41530eec3d06a4fad5bd00f3317071cfc` |
| `specs/140-user-account-billing/contracts/yookassa-integration.md` | `4524a7cb83b8dd9c3a24a70e162b54480ac602c63c03027980428987254740ae` |
| `apps/server/src/twobrain_rec_server/billing/database.py` | `b75f7a35952b8725ac1017e926ddea3449f480c71de0d6b3a7f83ae49fe6197f` |
| `apps/server/src/twobrain_rec_server/billing/registry.py` | `9bfd35b0050b8da9d96c2b1561fcb18bafb06a1cbd3f3747edd66d5df0736901` |
| `apps/server/src/twobrain_rec_server/billing/storage.py` | `6db2b1c5a52bc0fcdf573ffed883f956b76a8ff8f4896f0bee92487dd74cbefa` |
| `apps/server/src/twobrain_rec_server/db/models/billing.py` | `146c5c83debc274027de8e6630c7389a6a16c6ba018b48e446fd78b4f07f24bb` |
| `apps/server/src/twobrain_rec_server/db/tenant_context.py` | `a7dc09e2b153344d5d3cf2f71dedaffba875995460d13342ad19389885b1762c` |

## Контрольные суммы reviewer-owned checklist после добавления результата

| Путь | SHA256 |
| --- | --- |
| `checklists/requirements.md` | `8ec25571fd0a01a36c405cf9fc9823e5329218e4f738da2c63074c9a2f321898` |
| `checklists/payments.md` | `97b99ab9956295248ae10252a28afd13c3e7311dd387d7eec8e5e43f315238f5` |
| `checklists/operations.md` | `ed75a8c7f5c89cbc651894d08380a48058cba42bcb30475e04089a870460c665` |
| `checklists/security.md` | `e1210f57cdb45dd5a5599a766a332380e61e601357cd40cb69ef1be117aa5b31` |
| `checklists/launch-readiness.md` | `99268dc6ac32dab5bce0bb1303bcd26cd412a0feb9edbca2f395eb94e1d3ade5` |
| `checklists/post-plan-readiness.md` | `ef0fe6b8090d7a8669e45660b8bd91669d6c093ab5b790ed81ab10b74e13e74d` |
| `checklists/product-market-2026.md` | `982a90af611b4a81447198b4a1c71cf918aef198fcf1e73971ce693c65e3756d` |
| `checklists/ux.md` | `1eb1c6e68689fbdc7bf99746a04320c895c2b1ca6ab8b40efb10609e54bee126` |

## Проверка собственных изменений

Повторно прочитаны все 8 списков; проверены уникальность 220 исходных CHK,
их неизменные отметки и 10 отдельных IMP в этом отчёте. Предметный PASS не
меняет 158/62 глобальных отметок. `git diff --check` прошёл перед передачей;
исходные требования, код, старый отчёт и GitHub не менялись reviewer-ом.
