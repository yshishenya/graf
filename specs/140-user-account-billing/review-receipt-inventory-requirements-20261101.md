# Независимая проверка требований F140/T077 O13 — 01.11.2026

Результат: PASS только по качеству требований O13/Q1–Q6.
Предметный checklist: 10 отмечены / 0 открыты; содержательных замечаний нет.
Это не приёмка реализации, чеков/доставки, финансов или полного O6/T077.
Исполнитель /root/f140_notification_content_review; диалог 01a1955c-cb77-78e3-8844-ffeabcb2d594.
Ветка codex/140-observation-receipts; HEAD/base a139c07581668adb269bb7960ad8b15c87668233.
Полоса high-risk-product / active Spec Kit slice. Только качество Q1–Q6 до кода.
Разрешены только этот отчёт и checklists/receipt-inventory.md; код, Git/GitHub,
БД, тестовые запуски, CI, Dev и данные не меняются.
Применён code-reviewer (/Users/yshishenya/.agents/skills/code-reviewer/SKILL.md).

## Собственное полное чтение текущих оригиналов

Журнал собственного чтения:
/Users/yshishenya/.codex/sessions/2026/11/01/rollout-2026-11-01T07-27-29-01a1955c-cb77-78e3-8844-ffeabcb2d594.jsonl.
Все пути ниже относительно specs/140-user-account-billing/.
Output IDs — неусечённые фактические выводы команд данного диалога.
Семь требований и восемь source fingerprints сверены с manifest:4cb95b.

| Путь | SHA-256 | Полные диапазоны и output IDs |
| --- | --- | --- |
| spec.md | d2f10f4a2a6e2aa1fa2e051df3ded5dbb5255ee2c10ecfb579246cb24ba345c8 | 1–60:f3ba83;61–125:e666dc;126–250:f3eb3e;251–370:1fc9dc;371–470:69ac3f;471–610:b36f68;611–750:1a01ca;751–901:93ef76 |
| plan.md | f2b40a4f7049ef6d6da911734f9dc5db43e9e93c631fe4ddc7f4e9026a1fa20c | 1–215:a2ffb6;216–420:1eb43c;421–601:c011c0 |
| tasks.md | 315ab6d2d93adffd234d9ec65d7ee6e8bb294def726ca84f6c6222a4a9cf4592 | 1–215:23d6af;216–452:a31c7e |
| quickstart.md | 07ab1007bbc0b3529cd5e8ca3e69aec1fb989fc6c878d39c64c0a73774fe0eb5 | 1–230:41881b;231–460:e0faf0;461–630:75947d;631–824:12a05d |
| research.md | 04757a411d77ecc6804828d7cdff93978911e5d8f7a5d9f86b499248a1fcdb64 | 1–230:7f3f3e;231–477:f6a663 |
| data-model.md | 7421569b6c111cd988c4a778405a5362beb3b12d2077ed065c502769e78a88dd | 1–215:985bdb;216–439:edde06 |
| contracts/operator-observation.md | d6bcbc77062347b680565561eecef6d9d5cfecd50ee8cebb6f6e55020d241883 | 1–205:0052b1;206–406:16df39;407–475:0eda43 |

Новая применимая зависимость contracts/yookassa-integration.md прочитана целиком
(226ae0), SHA-256 4524a7cb83b8dd9c3a24a70e162b54480ac602c63c03027980428987254740ae.
Исполнитель и диалог те же; применимость: registration vs delivery, canceled
немедленно/pending 3 дня, provider/refund/financial/secret границы.

## Происхождение и восстановление неизменных оригиналов

Переиспользовано собственное полное чтение того же исполнителя/диалога,
проверяемое по review-fair-use-inventory-requirements-20261101.md (SHA-256
2340c64b1979a3c1eb20143468b8c9e9c2a2a2e24a1d4da16831ff5ed46d6964),
review-fair-use-inventory-code-20261101.md (SHA-256
8febf9f0f766cb39c23ea7d65287de5d85daa6d1fa3725fe5eab6d140fe7ef6a)
и review-refund-inventory-requirements-20261101.md (SHA-256
d0ba125929eb5aa1520b684d4f807caf57d4c67da81d6ccd3ebc6349cbbf94c1).
Эти отчёты содержат исходные outputs/диапазоны и происхождение; их решения
O11/O12 не подменяют данное независимое ревью. Собственное первоначальное
чтение PRD1–1100/1101–1750/1751–2474 и status1–2385 ранее подтверждено точным
сопоставлением исходных output-блоков42/75/142 того же журнала. Восстановлена
применимость в оригиналах, без повторного чтения неприменимых разделов.

Семь изменённых оригиналов выше прочитаны заново полностью. Прямое сравнение
фактического текста всех 24 outputs с текущими диапазонами:01d09d,7/7PASS.
Неусечённое чтение AGENTS/spec-kit-flow/product-gates/development-process/
tracker-policy/YooKassa также сопоставлено побайтно. Усечённые попытки a6ad63,
04c55d и неполные части других выводов не используются вместо полного чтения;
их применимые документы покрыты указанными ниже полными выводами.

| Оригинал и диапазоны | Применимость и вывод данного назначения |
| --- | --- |
| AGENTS.md целиком | Полномочия reviewer, маршрутизация, язык, отдельные gates;80b286. |
| README/document-reading целиком | Источники/собственное чтение/происхождение;99e91c. |
| product-gates/spec-kit-flow целиком | Приватность/диагностика/только разрешённые изменения/независимый допуск;15a59c/80b286. |
| development-process/tracker-policy целиком | Владение/передача/неполная T077/Refs вместо закрытия;15a59c/3bd6bf. Полный tracker в3bd6bf проверен отдельно01d09d; усечённая средняя часть development заменена15a59c. |
| Constitution89–530 | Все 7 принципов, platform/workflow/governance, без изменения принципов;250c9e/226ae0. |
| PRD1–150/349–374/688–844/1031–1101 | Capture/общие обещания/диагностика/сервер/изоляция;aa00d6. |
| PRD1578–1777/2035–2072/2278–2326/2471–2474 | Privacy/deletion/audit/observability/отдельные приёмки/приоритет спецификаций;fe0c5b. |
| current-status179–217/451–470/529–622 | F272/F150/F140/F199: не возвращать заменённые stop/runtime gates, не принимать runtime по документу;fe0c5b. |
| release-and-validation171–244/410–443/646–692/758–770 | Полоса/точныйSHA+base/отдельныйFull+выпуск/fragment/legacy/Git/evidence safety;0a6509. |
| operations/security/billing-lifecycle целиком | Реакция/сроки/authority/egress/RLS/финансы;462134. История применяется с заменами Scope Summary. |
| registry-operator-import целиком | Общий магазин не inventory/guard/owner_unverified/24ч;468c07. |
| entitlement-degradation целиком | Только названная server capability/Record/Stop/существующие данные/export/delete;0a6509. |
| F278 spec158–203/295–302 | Полный Functional Requirements и единый учёт: FR041/оплаченный срок/реакция≤24ч; e781e9. Ошибочный несуществующий путь278-billing-lifecycle не использован, восстановлен фактический278-production-billing. |
| YooKassa integration целиком | Новая применимая зависимость/registration vs delivery/receipt canceled и pending deadlines;226ae0. |

17 неизменных контекстных сумм повторно совпали (828962). Полные пути и суммы
сохранены в прежнем собственном O12 requirements report и текущем выводе828962;
новые seven-input и source manifests отдельно проверены4cb95b. Неизвестных
новых применимых зависимостей не осталось. Исторические ссылки на canary,
macOS и выпуск не дают действия в этом назначении и не принимаются заново.

## Содержательная независимая проверка десяти пунктов

| Пункт | Решение и проверяемое основание |
| --- | --- |
| CHK001 | PASS. O13/Q1 и spec688–704 задают исходную BillingInvoice.plan_snapshot.receipt_observations map; root refunds_and_receipts сохраняет refund count/groups O11 и получает составной source. Receipts — отдельный source/scope=database_inventory/kind=current_state, всегда partial. Root и nested count не складываются. Model1–11 и plan83–109 не создают сущностей/прав. |
| CHK002 | PASS. Q2 различает invoice_count, только object root с missing/JSON-null map, invalid root SQL/JSON-null/non-object или non-null non-object map и допустимую empty object map. Invalid не missing; контейнер считается один раз, фиктивная observation не создаётся. Empty map не missing. Это измеримые условия без ложного полного нуля при повреждении/отсутствии map. |
| CHK003 | PASS. Q3 требует совместно 2 parent_kind × 3 status × 3 source=18 сочетаний; отсутствующий/NULL/нестроковый/иной компонент или scalar/array entry образуют одну unknown тройку. Сортировка parent_kind/status/source, непустые группы и count=sum(groups.count) определены. JSON duplicate keys допускают несколько entries; уникальность provider receipts не утверждается. |
| CHK004 | PASS. Q1/Q3 и research1–18 отделяют top-level payment receipt_registration от новой map. У map нет fallback из UI; выбирается вся видимая БД без фильтра дня/status/environment/shop/времени. Не обещаны текущий магазин, подлинность связи, immutable revalidation или финансовая сверка. |
| CHK005 | PASS. Q4 не читает registered_at/observed_at/created_at, pending_since не существует; pending_age_seconds/escalation_due/reconciliation_gaps=null. Обе coverage=partial. Nested priority unrecognized→invalid_container→missing_observations→timing_and_reconciliation_uninstrumented; root учитывает ещё unknown refund и имеет финальное reconciliation_uninstrumented. Empty БД 0/[]/null; схема/доступ/БД дают whole-report safe отказ O2/O3. |
| CHK006 | PASS. Q2/Q5, plan и research задают CASE до json_each только над object map, type checks для root/map/entry; malformed не вызывает ошибку раскрытия. Две SQL-агрегации containers/groups достаточны для существующего SQL JSON. JSON/ORM rows не загружаются в Python, JSONB миграции нет; настоящие NOT NULL/FORCE RLS сохраняются. Защитный SQL NULL отдельно. |
| CHK007 | PASS. Q5 ограничивает чтение внутри SQL разрешённым path и parent_kind/status/source/count; Python/выход не получает JSON/key/ID/shop/environment/contact/amount/timestamps/URL. Record/merge/provider/почта/analytics/writers запрещены. O1/O2/O5 сохраняют guard/READ ONLY RR/as_of/cleanup и 15с/5с/2с/500gaps/64KiB. Новых полномочий/службы/зависимостей нет. |
| CHK008 | PASS как достаточность плана, не запуск тестов. Q6+quickstart87–114: RED, реальный CLI/изолированная PG/FORCE RLS; все 18 комбинаций, несколько entries, malformed root/map/entries/NULL/missing/{}, приоритеты, разные дни/снимки/новый процесс, sentinels/no-write/fingerprints/provider=mail=0/schema/identity/SET ROLE. Реальный SQL NOT NULL отвергается отдельно, защитная ветвь не ослабляет схему. Owned Python/__file__/XML/log/nodeids/hashes/finally cleanup и минимальный affected набор названы. |
| CHK009 | PASS. Все 7 текущих оригиналов согласованы с реально прочитанным сохраняющим путём: reconciliation21–25/73–81/230–260/324–499, receipts целиком, webhook750–805, provider_scope75–190, model141–160 и migration0044:1–90/195–217. Cap именно 16 entries, не 64. Дубликат статуса не освежает observed_at; registered_at опционален. Canceled немедленно/pending 3 дня, fair-use≤24ч/transient15мин+24ч/registry иF278FR041≤24ч не перенесены. |
| CHK010 | PASS. Q6/O8/plan/tasks/quickstart требуют независимый checklist/analyze/существующую #4932 до кода, после реальные проверки/review/converge/три exact-SHA/base PR gate. Все 87 полных task lines побайтно равны HEAD, T077[ ]; только Refs. Все 18 существовавших checklists неизменны:246 отмечены / 58 открыты. Полный FR089/O6, исторический пропуск чтения до PR7884/непринятый весь O8 и внешние приёмки сохраняются. Новой task/issue/выпуска нет. |

## Статические предпосылки и минимальность

- Собственные source выводы38ce17/e781e9/aa24c0/f6fa1a/bbbe95/b0b496 проверяют реальные
  helpers/caller/model/migration и текущее включение refund collector.
  Внешний source findings — указатель, факты сверены с оригиналами.
- record_observed_receipt связывает payment с operation/invoice либо refund
  с observed refund/invoice. merge хранит provider identity/environment/shop,
  status/source/optional registered_at/local observed_at. На одинаковом статусе
  возвращает duplicate до новой записи. Cap 16 ограничивает текущий writer,
  но не доказывает форму всей истории. Top-level registration обновляется
  только для payment; receipts.py допускает её без map. Это объясняет оба
  missing/invalid count и отказ от возраста/уникальности.
- BillingInvoice.plan_snapshot — SQL JSON NOT NULL, не JSONB, а JSON null
  допустим независимо от SQL NOT NULL. Миграция0044 включает invoices в RLS
  inventory и вызывает ENABLE/FORCE policy. Положительная проверочная схема
  обязана сохранять это. Текущий PG fixture уже включает BillingInvoice
  в TABLES/fingerprint/проверку forced RLS; изменять DB для допущения NULL нельзя.
- Текущий monitoring._refund_inventory — одна status/source агрегация.
  Добавление двух конкретных invoice агрегаций в том же снимке достаточно:
  первая считает контейнеры, вторая закрытые группы через guarded json_each.
  Ограничено 19 группами. Новая таблица, служба, общая JSON-система или Python
  загрузка частных снимков не нужны. Это оценка проектирования, не проверка
  ещё не написанного SQL и не эксплуатационное доказательство времени запроса.
- Прежний полный source audit остальных семейств не повторялся. Источник
  refund не переопределяется; новое разрешённое чтение JSON относится только
  к receipt helper Q5 и явно уточняет прежний запрет R5 для этого расширения.
- Scoped analyze-receipt-inventory-20261101.md прочитан целиком (f6fa1a):
  шесть Q требований / одна исходная T077 / 100% связей / 0 новых замечаний. Заявления
  его автора о 243 issues и единственной OPEN #4932 отмечены как его доказательства;
  GitHub в этом независимом назначении не запрашивался/не менялся.

## Ограничения и сохранённый остаток

Проверены требования и статические предпосылки. Новые unit/PG/CLI/снимки/
privacy/no-write сценарии не запускались, и никакого результата реализации
или runtime здесь нет. Отметки относятся только к качеству Q1–Q6.
Конституционные I–VII сохранены по области, денег/согласия/данных/полномочий/
провайдеров/capture/Dev/релиза не менялось. Legacy Impact untouched.

Порядок после допуска: исходная #4932/анализ → RED → минимальная реализация →
новые и затронутые проверки → независимые code review/converge → обязательные
точные SHA/base PR gates. T077[ ]/#4932OPEN, весь FR089/O6 и 58 прежних gaps остаются.
O6 включает все источники, постоянные attempts/errors/retries, регулярный
heartbeat, тревоги/retry и durable detected→contained→owner_assigned→notified→
investigating→resolved|accepted_risk. Сроки и внешняя приёмка не приняты и не
перенесены. Исторический O8 пропуск до PR7884 не исправляется задним числом.

Изменены только checklists/receipt-inventory.md и этот отчёт; остальные файлы
в рабочей копии принадлежат основному исполнителю и сохранены.
