# Независимая проверка требований F140/T077 O12 — 01.11.2026

Результат: PASS только по качеству требований O12/F1–F6.
Предметный checklist: 10 отмечены / 0 открыты; содержательных замечаний нет.
Это не приёмка реализации, fair-use enforcement, удаления или полного O6/T077.
Исполнитель /root/f140_notification_content_review, диалог 01a1955c-cb77-78e3-8844-ffeabcb2d594.
Ветка codex/140-observation-fair-use; HEAD 4625146710762f12fb2f854fbbd41d8900146b6b.
Полоса high-risk-product/active Spec Kit slice; только качество F1–F6, до кода.

## Собственное полное чтение текущих оригиналов

| Путь | SHA-256 | Полные неусечённые диапазоны и output IDs текущего назначения |
| --- | --- | --- |
| spec.md | 2bb46cd0c1a56229b805020826b5c394896ad40570e49442e37058b9974c07c1 | 1–60:5bf177;61–125:86bf8d;126–250:e1f884;251–370:674597;371–470:472249;471–610:e7956a;611–750:efe9d9;751–883:fcac60 |
| plan.md | 541b831f259b4df9c995f2920f7539afda709c6d1ce6546a38b47affb0eb2947 | 1–215:59d1b4;216–420:d679b5;421–573:319574 |
| tasks.md | f37b52d4ddf7f8a36b56f50ca410172a7af19154bc02c13d38373a3f4cc5318c | 1–215:caaf94;216–444:70bdd7 |
| quickstart.md | 345236fe985477df29e569eb115e5265b126829bd040cc7f60543461476cd434 | 1–230:9116da;231–460:358806;461–630:f21d6d;631–796:a7386f |
| research.md | d32added43f00e206e658932dd93574196682ed1e9e58f4b1bcf9e94d2a85183 | 1–230:cd79d9;231–458:a5496f |
| data-model.md | b8aa76ae308f33b29d3a58aa5f3c399aa062bedaf54f14e21edea1776d4e2d18 | 1–215:bc2a80;216–427:e3b68d |
| contracts/operator-observation.md | d2677f946881c4aac82a96932cfde02d1418e230ce835b177f76f9db5a80563b | 1–205:4ffd27;206–406:185d4c |

Журнал собственного чтения:
/Users/yshishenya/.codex/sessions/2026/11/01/rollout-2026-11-01T07-27-29-01a1955c-cb77-78e3-8844-ffeabcb2d594.jsonl.
Output IDs в таблице обозначают фактические выводы команд с указанными
диапазонами в этом журнале. Усечённые попытки406413/3fe044/0a1daa/f368dc
не используются как доказательство полного чтения; они заменены отдельными
полными выводами. Ни чужой пересказ, ни fingerprint не заменяют чтение.

## Неизменные оригиналы и карта применимости

Собственное первоначальное полное чтение того же исполнителя/диалога
подтверждено исходными outputs, записанными в
review-refund-inventory-requirements-20261101.md и предшествующих собственных
отчётах. Контрольные суммы 16 неизменных входов сверены заново; совпали.
В предыдущем назначении проверено также точное содержимое исходных outputs
PRD1–1100/1101–1750/1751–2474 и current-status1–2385 по журналу42/75/142.
Эти источники не объявляются новыми runtime-доказательствами.
После сжатия восстановлены применимые оригиналы:

| Оригинал и диапазон | Применимость и текущие output IDs |
| --- | --- |
| AGENTS.md целиком | Маршрут, независимость, владение; e91e6a. |
| README/product-gates/spec-kit-flow целиком | Карта guidance, metadata-only, high-risk/checklist/analyze, граница reviewer;28d7e2. |
| document-reading.md целиком | Собственное чтение/происхождение/изменённые оригиналы;26c23a. |
| Constitution89–530 | Все семь принципов, общие ограничения/workflow/governance, без изменения принципа;907ad1+ffc108. |
| development-process целиком | Владение/делегирование/независимый допуск/передача проверенного результата;ffc108. |
| tracker-policy целиком | T077 открыта, Refs для частичного результата, отдельное закрытие;b76ad6 (полный отдельный вывод). |
| PRD1–150/349–374/688–844/1031–1101 | Общий продукт/capture/diagnostics/сервер/tenant;35aa33. |
| PRD1578–1777/2035–2072/2278–2326/2471–2474 | Privacy/deletion/audit/observability/отдельная приёмка/приоритет спецификаций;700723. |
| current-status179–217/451–470/529–622 | F272/F150/F140/F199: действующие границы и заменённые stop/runtime-gates;700723. |
| release-and-validation171–244/410–443/646–692/758–770 | Полосы, три SHA/base gates, отдельный Full/выпуск, fragment/legacy, Git/evidence safety;1fe0d4. |
| operations/security/billing-lifecycle целиком | Полный O6/сроки/authority/egress/RLS;122a9b. Исторические финансовые правила применяются с заменами Scope Summary. |
| registry-operator-import целиком | Общий магазин не inventory, guard/RLS/lock/owner_unverified/срок реакции;1bc79c. |
| entitlement-degradation целиком | Только названная серверная capability; Record/Stop/данные/экспорт/удаление сохраняются;26c23a. Новая применимая зависимость прочитана полностью. |
| F278 spec158–203/295–302 | Весь раздел Functional Requirements и единый учёт приёмки, в том числе FR041/оплаченный срок/реакция≤24ч;1fe0d4. |

Применимые требования доступны в контексте; прямые зависимости разрешены.
В назначении нет capture/app/provider/live денег/почты/изменения схемы,
Full/CD или выпуска; исторические ссылки на их приёмки не дают нового действия.
Исторический пропуск обязательного чтения до первоначального кода PR7884
не исправлен задним числом; весь O8 не объявляется PASS.

## Проверка фактических предпосылок

- FairUseReviewRecord: модель400–452; migrations0068/69/70/71 прочитаны
  полностью (e0e01e). NOT NULL state/starts_at/review_by, пять state CHECK,
  review_by>=starts_at и <=starts_at+interval '24 hours' сохранены.
  Миграция0074 FAIR_USE_LINEAGE_POLICY целиком (0a2336) сохраняет maintenance
  и lineage-границы, а исходная0068 включает ENABLE/FORCE RLS.
- fair_use.py целиком прочитан дважды (a54170/f983e8). create_review создаёт
  notice/restricted, UTC review_by+24h; _RESTRICTED_STATES содержит
  restricted/appealed/confirmed. persist_review создаёт переданный валидный
  state только новой строки; существующей не обновляет state/appealed_at.
  appeal_persisted_review действительно сохраняет appealed, но terminal
  cleared/confirmed не меняет. resolve_review только replace dataclass;
  сохраняемое решение/owner/evidence/incident closure этим не доказаны.
- Cabinet fair_use.py целиком и account_merge815–850/статический поиск
  потребителей прочитаны в0a2336. Cabinet называет confirmed подтверждением
  ограничения; account_merge явно использует include_confirmed=False.
  Это исключение конкретного потребителя не превращает confirmed в cleared.
  Рабочий общий классификатор/enforcement и durable resolution не принимаются.
- PostgreSQL timestamptz infinity может пройти существующий CHECK, например
  одинаковые +infinity starts/review. Это статическое свойство выражения,
  не утверждение о live строках. F3/plan требуют вложенный CASE с NULL/isfinite
  ДО арифметики; numeric EXTRACT(EPOCH) разность только конечных дат избегает
  infinity subtraction/float и считает 86400 истекших секунд независимо от DST.
  Нельзя полагаться на порядок вычисления AND как защиту от арифметики infinity.
- Область новых malformed-проверок отдельно synthetic SQL: NULL/unknown state,
  обратный/>24h срок не требуют DROP CHECK или nullable positive fixture.
  Real migrated schema обязана отвергать невозможные INSERT; persisted infinity
  проверяется на реальном типе/constraints. Нулевой срок допустим.
- monitoring.py текущий collector/кредитный образец/общая форма прочитаны
  (c09c50/cab190); новый fair-use источник ещё not_connected.
  Generic _groups выбирает timestamp/возраст и считает будущее invalid,
  поэтому F3/F4 требуют отдельную одну узкую SQL-агрегацию, без дат в Python.
- database.py и billing_monitoring CLI полностью перечитаны (cab190).
  Реальные login/current_user, отсутствие superuser/BYPASSRLS, контекст
  billing_reconciliation/billing и RLS on проверяются guard. READ ONLY RR
  и driver defaults заданы до hooks/первого SELECT; общий15с/statement5с/
  lock2с/64KiB/cleanup и безопасный whole-report отказ остаются прежними.

## Решение по десяти пунктам

| Пункт | Основание PASS |
| --- | --- |
| CHK001 | F1: source=fair_use_reviews, database_inventory/current_state; все видимые строки одного снимка независимо от report_date. Count не люди/нарушения/магазин/решения. Spec688–703, plan83–109, research fair-use и model согласованы. |
| CHK002 | F2: пять state; одна unrecognized для любого иного, включая NULL; непустые группы отсортированы, count=sum. confirmed не cleared и может сохранять restriction. Persist/appeal/resolve различены исследованием; terminal state не durable incident resolution. |
| CHK003 | F3: pending строго notice/restricted/appealed. Invalid сначала; затем starts>as_of, starts<=as_of и review<=as_of, starts<=as_of<review. Для валидного start<=review эти ветви исчерпывающие и непересекающиеся. Начало/срок равны as_of включены; zero-duration сразу reached; будущее нормально; terminal/unknown исключены. |
| CHK004 | F3/plan83–94/research требуют NULL/isfinite прежде numeric epoch difference, invalid при обратном или >86400s. Это elapsed, не calendar day/float/session DST. При null/nonfinite нет арифметики;23h/24h/25h на DST не смешиваются. |
| CHK005 | F4: никаких дат/возраста; reached не доказанная глобальная просрочка/доставка/решение. Всегда partial, deletion/reaction=null, строгий unrecognized→invalid_schedule→deletion_and_reaction_uninstrumented. Пустота0/[]/все pending0 не ошибка; schema/access/DB error — whole-report отказ O2/O3. |
| CHK006 | F2/F6/model/research отражают реальные NOT NULL/пять state/deadline CHECK и статические writer/consumer различия. Positive schema не ослабляется; malformed отдельно; сохраняемое снятие/закрытие не выведено из count/state. |
| CHK007 | F5 разрешает только state/starts_at/review_by/count в SQL, без дат/ORM в Python. IDs/связи/capability/reason/evidence/appeal/decision/contact/JSON не читаются. Persist/appeal/resolve/restrict/purge/provider/mail/analytics запрещены; O1–O5 guard/RLS/READ ONLY RR/as_of/limits/cleanup неизменны. |
| CHK008 | F6/quickstart87–119 задают RED, real PostgreSQL/CLI/forced RLS/constraints,5states,±1µs/равенства/будущее/zero/24h/DST/infinity/приоритеты, malformed SQL отдельно. Два снимка/новый процесс/fingerprints/no-write/privacy/схема/роли/SET ROLE и cleanup включены. Это достаточность плана, тесты ещё не выполнены. |
| CHK009 | Все7документов согласованы; FR107 сохраняет notice/appeal/≤24h и Record/Stop/export/deletion. Entitlement/operations/security/deletion/F278FR041 учтены. Transient15мин/24ч, fair-use≤24ч, receipt canceled немедленно/pending3дня, registry и FR041 реакция≤24ч не перенесены; полное O6 открыто. |
| CHK010 | F6/O8/plan/tasks требуют независимый checklist PASS и отдельный scoped analyze/существующую4932 до кода; затем RED/реальные проверки/independent review/converge/три exact-SHA/base gates. 87полных task lines совпали с HEAD, T077[ ],8старых checklist побайтно прежние162/58. Только Refs4932, без новой задачи/службы/ворот/релиза. Исторический пропуск O8 прямо сохранён. |

## Непринятый остаток и граница допуска

10отметок относятся только качеству F1–F6 перед кодом. CRITICAL0/HIGH0/
MEDIUM0 новых содержательных замечаний. Отдельный scoped analyze и сверка
существующей #4932 основного исполнителя обязательны до кода; их приёмка
не входит в назначение reviewer и не подменяется этим PASS.
Не принимаются полный FR089/T077/O6, удаление, general incident reaction,
heartbeat/регулярность/тревоги/повторы и неподключённые источники. Нет приёмки
T070/fair-use classifier/enforcement/durable resolution, настоящих писем,
финансовой/приватностной/ручной или выпускной приёмки. #4932 должна оставаться
OPEN; GitHub в этом назначении не читался и не менялся. Legacy Impact untouched.

Восемь прежних checklist прочитаны по всем58открытым строкам, без исправления
устаревших исторических условий через новый collector. Их исходные файлы
побайтно равны HEAD: requirements17/8;operations10/8;security11/6;payments14/6;
launch-readiness32/8;post-plan-readiness25/15;product-market36/4;ux17/3,
всего162отмечены/58открыты. Все87 исходных полных task lines сохранены,
исходная T077[ ]. O6 — работа в той же задаче, не отмена или новая issue.

Изменены только назначенные checklist и этот отчёт. Чужие семь требований
не редактировались. Код/Git/GitHub/данные/Dev/provider/почта/CI/Full/CD/
commit/release не менялись и не запускались. Тесты/линтер/hooks/PG/CLI не
запускались; выполнены только чтение и собственные read-only hash/line compares.

## Контрольные суммы неизменного контекста и новых источников

| Неизменный контекст | SHA-256 |
| --- | --- |
| AGENTS.md | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| .specify/memory/constitution.md | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| docs/prd-voice-layer-final.md | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| docs/current-product-status.md | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| docs/agent-guidance/README.md | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| docs/agent-guidance/document-reading.md | `5c3ab1f885dbf324edab70c0f4b7a5451208b3d7307c1ca7a5afdd7af0c8eb22` |
| docs/agent-guidance/product-gates.md | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| docs/agent-guidance/spec-kit-flow.md | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| docs/agent-guidance/development-process.md | `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864` |
| docs/agent-guidance/tracker-policy.md | `9793de5e158283c2d37bdd2b47f0daf4d312a44fd6ffa37cc22ac47f7a0c3472` |
| docs/agent-guidance/release-and-validation.md | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| specs/140-user-account-billing/contracts/operations-reconciliation.md | `23a4e9d8aee95b39efaeda39eecc577e737426a20cd4661874208fa543b95ed2` |
| specs/140-user-account-billing/contracts/registry-operator-import.md | `297bfe6c3acb063d70a6ef634c287a901fc9c342549270eaeec2c15a35c5b0a5` |
| specs/140-user-account-billing/contracts/security-privacy-compliance.md | `38934189b91e33a070b49e61673020d41530eec3d06a4fad5bd00f3317071cfc` |
| specs/140-user-account-billing/contracts/billing-lifecycle.md | `1d3e8fe3a672a34a4bc7a34bb6135800781d840e6e9350e0659bd142c5931ff7` |
| specs/278-production-billing/spec.md | `d452d625cf5035edcdd144c34561aeb2c5d1a19c29826c61505801a3dd53e09c` |
| specs/140-user-account-billing/contracts/entitlement-degradation.md | `5aa1ea33309ca3641c32e8c9ab08ace8df61459a24c559a9262d9f1ae62e8809` |

| Предметный источник | SHA-256 |
| --- | --- |
| apps/server/src/twobrain_rec_server/billing/fair_use.py | `4ee85c0c75684a1e3e457e0b3c4e58787180cef241934fd601be686c49d8f0b8` |
| apps/server/src/twobrain_rec_server/db/models/billing.py | `146c5c83debc274027de8e6630c7389a6a16c6ba018b48e446fd78b4f07f24bb` |
| apps/server/src/twobrain_rec_server/db/migrations/versions/0068_fair_use_reviews.py | `814152a113d6e3451af8949a5e55fa59f0135222fbc709b16fe439f1590e88ac` |
| apps/server/src/twobrain_rec_server/db/migrations/versions/0069_fair_use_review_constraints.py | `53a7d30110a47b97c3a1caca8d30403bb18267456168d0170315fcb7b1c9719d` |
| apps/server/src/twobrain_rec_server/db/migrations/versions/0070_fair_use_review_metadata_constraints.py | `996a88793ca1d37763faff73cebf5e0a70c97cf7b07f394a302a4dd38806d638` |
| apps/server/src/twobrain_rec_server/db/migrations/versions/0071_fair_use_capability_prefix.py | `6149828d9662e04994a05824002652535e82829a80df081313e38dd5fb7208ce` |
| apps/server/src/twobrain_rec_server/db/migrations/versions/0074_linked_workspace_and_merge_proofs.py | `8b85a649b62e46eaae219891fc4b4b4ce11ea8e3f56f6b99b1507912c4b29d52` |
| apps/server/src/twobrain_rec_server/cabinet/web_routes/fair_use.py | `d4357442d8abfd4430f3f3e478046e2aa5b09a3e2bab8d981e69409513e08c64` |
| apps/server/src/twobrain_rec_server/auth/account_merge.py | `7840869e398b8f621d78c27119a7ecbba15f4f6058fac1d7f54e1dd4f598e205` |
| apps/server/src/twobrain_rec_server/billing/monitoring.py | `08d5a34627bf2ff9ff5a32f8803cccbf963f8a490f3ea292f3692e2893a578f1` |
| apps/server/src/twobrain_rec_server/billing/database.py | `b75f7a35952b8725ac1017e926ddea3449f480c71de0d6b3a7f83ae49fe6197f` |
| apps/server/src/twobrain_rec_server/cli/billing_monitoring.py | `68ca13c2e36f1958124d2a60300b326941d73f34d481f4834afe18abac1aab55` |

## Проверка фактических outputs семи оригиналов

- spec.md: 1–60: journal6726/call_347d368e91824a52abc56f0c28f4057b; 61–125: journal6731/call_c971474a3ff64de8ade5eb6086557ffe; 126–250: journal6738/call_8b34d26723014b528324e0d4d1d8bb0e; 251–370: journal6745/call_4c1a0b0f25ca4bd9b98e1c076377efec; 371–470: journal6750/call_eac9dd15b86b454093faeab23cecd1b3; 471–610: journal6757/call_70abc3ea42d74a88a38353fd1ebcc5ff; 611–750: journal6764/call_e65113a0c468408987eb80b96d3fe257; 751–883: journal6769/call_c1a5eaf6e4be4bd58dfde0fa8cef5170. Полное точное совпадение с текущим оригиналом, без усечения.
- plan.md: 1–215: journal6777/call_e820d022b3f0441eb8f12bdd103a260f; 216–420: journal6787/call_eb55f20212c3487b8f0357697e234857; 421–573: journal6792/call_bf1aa52c5a8d4543b853286c6fc0900e. Полное точное совпадение с текущим оригиналом, без усечения.
- tasks.md: 1–215: journal6801/call_cf72c36c98534f3989387e0388ce31dc; 216–444: journal6806/call_2911c701bbad4c94833491cf3cf05883. Полное точное совпадение с текущим оригиналом, без усечения.
- quickstart.md: 1–230: journal6814/call_861aa11998924dd1acf77b36be349bad; 231–460: journal6819/call_7fd00ec2e3c54475b0ebe949fb299d99; 461–630: journal6843/call_d328cad35c9747acb22af3f9c9f19570; 631–796: journal6848/call_192686891ac04811a9c1cc9cdb572b97. Полное точное совпадение с текущим оригиналом, без усечения.
- research.md: 1–230: journal6858/call_186f0eb8ba204e7a8e2562c1c81b25be; 231–458: journal6863/call_4dc24342e12a40f59589ee3b8173d71e. Полное точное совпадение с текущим оригиналом, без усечения.
- data-model.md: 1–215: journal6871/call_b68c68d63c224cfc85f13af3818352f6; 216–427: journal6876/call_c14a57af067d4b1db042384bec7aa6b7. Полное точное совпадение с текущим оригиналом, без усечения.
- contracts/operator-observation.md: 1–205: journal6883/call_f52413d6fbcb44699714655772b608ff; 206–406: journal6888/call_78d88f796f054c4795772eaa0bfd355e. Полное точное совпадение с текущим оригиналом, без усечения.

Итоговая перепроверка: семь изменённых оригиналов и29 контекстных/source
входов совпали с записанными SHA-256 (36/36). Сами23 исходных output-блока
сравнены с точными текущими диапазонами:7/7документов полностью совпали,
без усечения. Checklist перечитан полностью:10отмечены/0открыты.
Отчёт перечитан1–105/106–конец; собственные файлы без trailing whitespace.
После появления чужого analyze он сохранён и не редактировался; тесты не
запускались. Допуск относится только F1–F6 указанного содержимого.
