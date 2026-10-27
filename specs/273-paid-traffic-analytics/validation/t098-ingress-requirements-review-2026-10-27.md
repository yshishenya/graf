# F273/T098 — независимое ревью требований полного SNI-входа

Дата: 27.10.2026. Проверяющий: отдельный агент `/root/growth_infra_gate`.
Рабочая ветка: `codex/273-ingress-origin`; исходный HEAD:
`0a1bce3505cd1582ccda552ba4ac10b4c4258d26`.
Активный указатель и `check-prerequisites.sh --json --paths-only` указывают
на существующую F273, задача T098, issue #7698. Локальные изменения требований
проверены отдельно от HEAD; точные SHA-256 приведены ниже.

**Результат: PASS качества требований — 117 подтверждены, 0 открыты.**
Прочитан и независимо оценён каждый действующий вопрос четырёх чек-листов,
включая шесть новых. Предыдущие отметки не использовались как доказательство.
Это разрешает пройти следующие ворота анализа и синхронизации задачи;
реализация, рабочая приёмка и выпуск не приняты. T098 остаётся открытой.

Область: существующий high-risk Spec Kit slice, инфраструктура и приватность.
Изменены только четыре назначенных reviewer-owned чек-листа и этот отчёт.
Код, spec/plan/research/quickstart/tasks, Git/GitHub, серверы и данные
проверяющий не менял. Команды SSH, нагрузочные прогоны, отправки и оплаты
не запускались. Исходный design-report сохранён без изменений.

## Что проверено и как ограничено чтение

Полностью прочитаны текущие spec, plan, tasks, research, quickstart,
data-model, legal-basis, четыре контракта и конституция; каждый действующий
пункт четырёх чек-листов перечитан перед фиксацией и после неё. Последнее
уточнение quickstart о методе ресурсной пробы прочитано повторно целиком.
Применены guidance README, document-reading, spec-kit-flow и product-gates.
В release-and-validation прочитаны применимые разделы validation lanes,
production/closeout, Full/CD, restore cadence, Legacy Definition of Done
и Git/evidence safety. Настоящий отчёт не заявляет чтения всех несвязанных
разделов выпускной инструкции.

Перечитаны зависимости хранения/измерения: backup-restore, provider-rollback,
capacity-baseline, legal-basis-records, product-activation-analytics;
в posthog-runbook — Data Scope, Autocapture, Session Replay, resource thresholds,
Threshold Scopes, observer, owners, RBAC/MFA/revocation, backup/retention,
readiness, capacity, rollback, T118/T119. В reports — состав R01–R14,
оговорки, freshness, owners, расход, suppression, campaign consistency,
состояние применения и карта требований. Исторические receipts не принимаются
как новое рабочее доказательство.

Для неизменных PRD/current-status использовано прямое scoped-разрешение
владельца F273 от 22.10.2026: перечитать затронутые требования и зависимости
хранения, сверить SHA остальных ранее прочитанных документов. Проверены все
7 из 7 исходных хешей этого разрешения; совпали. Это не заявление о новом
полном чтении двух больших неизменных документов. Ослабление согласия,
проверок, защиты данных или выпуска разрешением не предусмотрено.

## Замечания этого прохода и их устранение

1. В первом прочитанном варианте чисел 100 / 70% / 10 мс не хватало
   определения длительности, выборки, измеряемого времени и области максимума.
   Исполнитель уточнил quickstart до финального ревью. Сейчас задано:
   10 прогревочных запросов на маршрут; 100 TLS keep-alive соединений поровну
   по default/special не менее 30 секунд; каждую секунду FD/socket FD каждого
   worker, включая дренирующие поколения; максимум каждого отношения строго
   <0,70. Неполные данные означают INCOMPLETE. Задержка — 500 новых соединений
   на baseline и candidate в окнах не менее 60 секунд, открытый темп 8/с,
   TCP connect → первый HTTP-байт с TLS, monotonic; nearest-rank p95 отдельно
   для каждого маршрута, прирост <10 мс. Пропуск/ошибка/timeout — FAIL.
   Это достаточно однозначный инженерный критерий, выбранный исполнителем,
   не измеренная рабочая ёмкость и не замена T097.
2. Общее «без wildcard/reuseport» могло противоречить сохранению исходного
   public bind. Финальный quickstart ограничивает этот запрет новыми внутренними
   loopback-сокетами; исходные публичные привязки сохраняются. Замечание снято.

Правильный rec SNI с чужим Host получает 421 до API; UNKNOWN — 400 до API.
Ручные billing/share installers перечислены как читающие тот же rec-файл:
во время перехода запрещены, после него сверяются с конечным набором.
Штатный CD не выдан за их автоматический вызов, платёжных проб ради T098 нет.

## Матрица infra — 29 из 29

| Пункт | Вывод | Конкретное основание качества требования |
| --- | --- | --- |
| CHK001 | PASS | FR-033/052; operations «Резервное копирование»: существующий сервер, точный локальный каталог, root 0700/0600. |
| CHK002 | PASS | FR-034/052/053: внешних копий 0; потеря узла/диска может уничтожить всю историю; новое измерение с пробелом. |
| CHK003 | PASS | backup-restore «Scheduled Automation» и runbook: ежедневное копирование 02:30 UTC. |
| CHK004 | PASS | FR-051; failed/partial блокирует готовность, оповещает, не вытесняет пригодную копию и не останавливает продукт. |
| CHK005 | PASS | FR-052: последние 7 полных успешных наборов, минимум 2; manifest/inventory и новый набор проверяются до ротации. |
| CHK006 | PASS | FR-034: от успешного окончания 0≤age<26h; failed/future/unknown/≥26h и неполный набор закрывают готовность. |
| CHK007 | PASS | SC-010; backup-restore: дни 1 и 15, 04:30 UTC; актуальный согласованный результат возрастом <30 суток. |
| CHK008 | PASS | FR-053; operations T118: холодная согласованная точка, привязанный runtime/config/images, нативное и PostHog ORM/event-query чтение всех классов; tar/health отдельно недостаточно. |
| CHK009 | PASS | FR-051; operations T118: failure/timeout/cleanup не дают PASS, вернуть только прежде работавшие службы; продукт и его данные сохраняются. |
| CHK010 | PASS | FR-053; backup-restore: потеря после последней точки/неpersisted ingestion отдельно; без всех локальных копий история не восстановима. |
| CHK011 | PASS | SC-012; operations «Нагрузка сайта»: 5/20/15 минут, 5×R, заданные адреса/доли, ошибки и недостигнутая частота делают FAIL. |
| CHK012 | PASS | SC-012: R — nearest-rank p95 минутных внешних HTML GET/60 за 10 080 полных UTC минут; unknown не ноль. |
| CHK013 | PASS | FR-032/058; anonymous-aggregate: счёт при запросе без внешнего сетевого вызова/зависимости от PostHog. |
| CHK014 | PASS | FR-032; operations и provider-rollback: отключается измерение; login/upload/record/review/account/legal остаются доступны при частичной деградации. |
| CHK015 | PASS | FR-058; Edge Cases и scenario6: отказ внешнего счётчика не меняет сайт и уровень1; отражается как measurement gap. |
| CHK016 | PASS | FR-031/032; operations T116: непересекающиеся классы, общий FS один, совместные причины видимы, одно защитное действие. |
| CHK017 | PASS | operations и runbook Threshold Scopes: CPU/memory/host-load только alert; shared-FS <20% отдельно относится к аналитической защите. |
| CHK018 | PASS | SC-009; operations, runbook: ≤15 минут для analytics/host/backup/restore/retention/alerting; фактическая учебная доставка отдельно. |
| CHK019 | PASS | research §5, operations observer: существующий astraglobal, GET/TLS/200/JSON раз в60s, timeout10s, два отказа, прямой канал без цели. |
| CHK020 | PASS | FR-056; независимый channel-check, ошибка/unknown/недоставленное не PASS; канал не подтверждается сообщением в него же. |
| CHK021 | PASS | FR-055; runbook Named Owners: роль на каждое правило, обязательное разрешение роли в имя вне Git, alert_owner_unnamed наблюдаем. |
| CHK022 | PASS | FR-039; capacity-baseline/T116: allocated bytes по классам, сравнимые полные замеры ≥24h, рост/1000 событий, прогноз и FS отдельно. |
| CHK023 | PASS | operations «Начальные численные пределы»:128GiB,≤0,5GiB/сутки,≥90суток запаса; infra_operator, пересмотр21.11; unknown не0. |
| CHK024 | PASS | operations:20% защита,10% критическая тревога; план расширения за28суток, решение за7; не удалять историю/не поднимать порог ради PASS. |
| CHK025 | PASS | Edge Cases; operations и rollback/restoration: config/runtime/version сверка, provider/page smoke, продукт сохраняется, новая readiness не возникает от флага. |
| CHK026 | PASS | plan «Полный вход T098»: общий443→10445 rec,10446/10447 strip→прежние upstream, nginx1.24, полный include graph и lock; прототип не рабочая приёмка. |
| CHK027 | PASS | scenario8: отдельные IPv4/IPv6, недоступный IPv6 не PASS; effective timeout/buffer/half-close/keepalive, actual special клиент/соседи; полный численный метод пробы выше. |
| CHK028 | PASS | plan A/B/C/D и обратный переход: receivers сохраняются до дренирования старых workers; late ClientHello, ≤15мин наблюдения, без kill чужих сессий. |
| CHK029 | PASS | Legacy Impact: retain-with-exception только перехода; owner/expiry03.11/removal trigger/risk/validation/T098#7698; старый bypass запрещает приёмку. |

## Матрица security — 27 из 27

| Пункт | Вывод | Конкретное основание качества требования |
| --- | --- | --- |
| CHK001 | PASS | spec «Правовая конструкция», FR-061: уровень1 без идентификаторов, уровни2/3 персональные/псевдонимы, IP отдельная категория, не обезличивание. |
| CHK002 | PASS | FR-008 и product-gates: содержимое встреч, аудио, секреты, токены, private paths не разрешены расширением хранения. |
| CHK003 | PASS | FR-008/Legacy Impact отсылают к существующим запретам093/094/096; FR-061 ограничивает новую категорию, не создаёт новый конфликтующий каталог событий. |
| CHK004 | PASS | FR-048: остановка обработки, отдельный deadline/owner/охват/результат; until_decision не срок исполнения; без срока случай не закрыт. |
| CHK005 | PASS | plan и activation-analytics «Provider Boundaries»: first-party self-hosted PostHog по разрешённым событиям; Yandex/offline только выделенный набор и основания; Telegram только metadata. |
| CHK006 | PASS | FR-054; operations, runbook и scenario8: visitor/user/IP/payload в оповещениях и доказательствах запрещены. |
| CHK007 | PASS | FR-028; legal-basis-records: recipient/purpose/state/basis/scope/роль/дата/evidence_ref проверяемы; отсутствующая или неизвестная запись запрещает передачу. |
| CHK008 | PASS | FR-002/029; legal-basis-records: advertising_attribution не заменяет отдельное subscriber prior consent. |
| CHK009 | PASS | FR-049; legal-basis-records: прекращение передачи сразу даже pending/failed доставки отзыва; запрет повторной передачи, подтверждение получателя отдельно. |
| CHK010 | PASS | FR-036/050; data-model: явный until_decision на каждую категорию, включая network_access_metadata; 90дней — применимость источника, не удаление. |
| CHK011 | PASS | operations/data-model: ClickHouse provider events, GRAF PostgreSQL aggregate/attribution, отдельная public.network_access_metadata; конкретные локальные копии. |
| CHK012 | PASS | FR-050: missing/unknown/error закрывает готовность; проверка ежедневно, возраст0≤age<26h, restore инвалидирует старое доказательство. |
| CHK013 | PASS | FR-036/048; data-model/records: case_ref, selector, основание, owner,deadline,результат/rows_affected; без deadline не исполнять/не закрывать. |
| CHK014 | PASS | Constitution IV; FR-003/049/053: запрос внешнему получателю не объявляется исполненным purge, границы контроля и потеря истории видимы. |
| CHK015 | PASS | network_access_metadata зарегистрирована в data-model, operations и legal-basis-records; семь полей, цели/основание/раскрытие/права/аудит/копии до writer. |
| CHK016 | PASS | FR-001/006/Legacy: optional только explicit opt-in, default-on запрещён. |
| CHK017 | PASS | FR-059; data-model Consent: missing/corrupt/unreadable решение запрещает все optional цели. |
| CHK018 | PASS | FR-002; независимые analytics/advertising_attribution/behavior_replay; одна цель не включает другие. |
| CHK019 | PASS | FR-003; scenario5: решение соблюдается до следующей записи/передачи и при следующем визите; смены решения определены. |
| CHK020 | PASS | anonymous-aggregate «Границы»: не читает/не пишет consent, не узнаёт повторного посетителя. |
| CHK021 | PASS | FR-037; runbook: ≥2 accepted operator memberships, pending invite не считается, TOTP до доступа; без этого fail-closed. |
| CHK022 | PASS | FR-038; runbook/Restoration: версионируются конфигурация и installed guard; runtime/readback сравнивается с ревизией. |
| CHK023 | PASS | FR-055; operations/Named Owners: роли infra/analytics/product и обязательная закрытая привязка ответственного. |
| CHK024 | PASS | FR-060; runbook: revoke в день смены роли, rotate доступные секреты, audit/review до возобновления; metadata-only receipt. |
| CHK025 | PASS | FR-044/047; operations approval: право отдельно от privacy/security/QA/rollback/delivery; кто/что/когда и область до запуска, флаг не основание. |
| CHK026 | PASS | FR-062; scenario8: источник≠transport peer, local/Docker/host-network, fake headers/UNKNOWN, exact peer, direct API, SNI/Host и recreate проверяются отдельно. |
| CHK027 | PASS | FR-061; plan/scenario8: без HTTP realip, сохраняется transport remote_addr, relay access_log off, error/stream/application logs проверяются; семь полей/writer gates неизменны. |

## Матрица privacy-measurement — 45 из 45

| Пункт | Вывод | Конкретное основание качества требования |
| --- | --- | --- |
| CHK001 | PASS | spec три уровня и FR-061: разные данные, основания и storage; IP отдельный, никакой implicit личности уровня1. |
| CHK002 | PASS | FR-010; data-model общий запрет и aggregate contract: IP/session/UA/fingerprint/cookie/pseudonym/связь визитов исключены. |
| CHK003 | PASS | legal-basis:152-ФЗ ст3п1/9,ст6ч1п5/7; ограниченияп9/ст15 описаны, согласие уровня3/38-ФЗст18 отдельно. |
| CHK004 | PASS | spec/research§1: сохранённый ключ делает псевдоним персональным; aggregate contract запрещает pseudonym import. |
| CHK005 | PASS | spec/data-model: атрибут с регистрации и аккаунтные вехи по договору; анонимная история не восстанавливается через IP/время. |
| CHK006 | PASS | Out of Scope/FR-007: определяемый optional посетитель без согласия запрещён; основание уровня2/IP отдельно, контент внутренних страниц не расширяется. |
| CHK007 | PASS | FR-047 и operations approval: reviewer/роль, что/когда/область/подтверждение; устное историческое одобрение не заменяет запись. |
| CHK008 | PASS | FR-003: до следующей записи/передачи после принятия решения сервером, а не неопределённое «немедленно». |
| CHK009 | PASS | FR-004: то же число действий и заметность; scenario5 проверяет отзыв/повторный визит. |
| CHK010 | PASS | FR-001/006, Clarifications: default opt-in и запрет default-on согласованы. |
| CHK011 | PASS | data-model переходы consent: no decision→granted/denied, granted→denied; повторное решение и версия учитываются. |
| CHK012 | PASS | FR-059: corrupt/unreadable/missing = запрет необязательных целей. |
| CHK013 | PASS | FR-003/007/009/048: отказ не выключает агрегат; цель3 прекращается; уровень2/IP только по своему действующему основанию. |
| CHK014 | PASS | FR-005: отдельно назвать согласованное/обезличенное измерение и путь отказа; FR-046 сверка опубликованных текстов. |
| CHK015 | PASS | anonymous-aggregate: consent хранится ради соблюдения решения, не источник измерения. |
| CHK016 | PASS | SC-002 и aggregate contract: разбор сохранённых записей/response headers; запрет идентификаторов проверяется не чтением одного кода. |
| CHK017 | PASS | data-model/aggregate: длина/allowlist/нормализация, похожие на email/телефон/имя метки не сохраняются. |
| CHK018 | PASS | data-model: desktop/mobile/tablet/unknown; ru/non_ru/unknown, без города/координат/нового внешнего IP-запроса. |
| CHK019 | PASS | FR-057: порог3 по полному ключу, подавление1–2 до суммирования/разностей; число запросов не число людей и не самостоятельное доказательство. |
| CHK020 | PASS | FR-013/062; scenario8: exact проверенный peer, реальные внешние выходы/оператор, служебные маркеры и защита от подделки. |
| CHK021 | PASS | aggregate contract: не читать/не писать consent и не создавать cross-visit связь. |
| CHK022 | PASS | FR-017/handoff: last non-direct только допустимо сохранённых источников; анонимный возврат без основания — текущий визит/unknown/direct. |
| CHK023 | PASS | FR-017; reports campaign consistency: одно окно90дней и разрешённая история; различный охват не устраняется незаконной склейкой. |
| CHK024 | PASS | FR-018/024; data-model: отсутствие кампании = unknown, не придуманная кампания. |
| CHK025 | PASS | FR-024; handoff и reports: unknown отдельная строка, direct по отдельным признакам, отрицательная сверка предусмотрена. |
| CHK026 | PASS | FR-025; activation contract: и клиент и сервер; устойчивый аккаунт+веха, restart/multiprocess/multidevice, uncertain delivery не повторяется вслепую. |
| CHK027 | PASS | FR-023; handoff/activation: закрытый linked/weak/unknown и точные условия. |
| CHK028 | PASS | FR-022; handoff: основной путь browser account и резервная ссылка приложения; межустройственная связь только при разрешённом основании. |
| CHK029 | PASS | FR-019: GET200/full expected bytes/no disconnect; HEAD/3xx/206/error не выдача, неизвестное не успех, установка не доказана. |
| CHK030 | PASS | activation contract: реальные desktop/auth/visible result триггеры каждой вехи и отдельная browser-upload ветвь без приписанной установки. |
| CHK031 | PASS | SC-009; operations/runbook: все классы≤15мин, полная потеря цели отдельна от частичной деградации. |
| CHK032 | PASS | FR-031/032; operations T116: общий FS один, классы непересекаются, host alerts и analytics protect разделены, совместный переход один. |
| CHK033 | PASS | FR-033/052; operations: конкретный локальный каталог существующего узла и root права. |
| CHK034 | PASS | FR-052/053: offsite0 принято; host/disk loss может уничтожить всю историю; локальные архивы не disaster recovery. |
| CHK035 | PASS | FR-036/050; operations retention: until_decision по каждой категории; IP отдельно; consent/session validity/90day eligibility не продлеваются. |
| CHK036 | PASS | FR-050: missing/unknown режим ошибка, блокирует readiness; daily proof/freshness/restore invalidation определены. |
| CHK037 | PASS | FR-034: successful complete, минимум2,0≤age<26h; unknown/future/failed/≥26h блокируют. |
| CHK038 | PASS | SC-012/operations:10 080min nearest-rank baseline, R→5R→R,5/20/15min и закрытые отрицательные критерии. |
| CHK039 | PASS | Таблица связи SC001–013 с FR приведена ниже; scenario1–8 и contracts задают проверяемые исходы. |
| CHK040 | PASS | FR-040; reports:14 PostHog R01–R14 и10 Yandex, источник/разрезы/пустое/назначение; actual apply честно отдельно. |
| CHK041 | PASS | FR-042; reports:владелец каждого R, consent/internal/gap/unknown/deletion caveats; freshness26h,R14семь дней. |
| CHK042 | PASS | Assumptions/plan: первый paid Яндекс.Директ, macOS-first+web; текущий органический старт не выдаётся за paid launch. |
| CHK043 | PASS | Legacy Impact:093/094/096 запреты/каталог/границы сохраняются; временный ingress exception не меняет consent. |
| CHK044 | PASS | FR-044/047 и scenario final: техфлаг не одобрение; платный запуск отдельно, нынешний PASS не release. |
| CHK045 | PASS | plan Pending decisions и роли: операторские конфигурация/второй оператор/рабочая приёмка с ответственными; unknown закрывает readiness. |

## Матрица requirements — 16 из 16

RQ01–RQ16 — только локальная нумерация шестнадцати вопросов в исходном порядке;
новые идентификаторы в чек-лист не добавлялись.

| Пункт и исходный вопрос | Вывод | Основание |
| --- | --- | --- |
| RQ01: No implementation details (languages, frameworks, APIs) | PASS | Spec формулирует наблюдаемые границы/результаты. Техническая конструкция в plan/research; порты Legacy — проверяемая граница временного исключения, не алгоритм реализации. |
| RQ02: Focused on user value and business needs | PASS | Цель/US1–5: достоверная воронка, источники, стоимость активации, устойчивое измерение и обратимое решение запуска. |
| RQ03: Written for non-technical stakeholders | PASS | Определены роли, уровни, согласие/отказ и бизнес-вопросы; необходимые обозначения объяснены контрактами. |
| RQ04: All mandatory sections completed | PASS | Clarifications, context, roles, US/testing, edges, FR001–062, entities, SC001–013, assumptions, legacy и exclusions заполнены. |
| RQ05: No [NEEDS CLARIFICATION] markers remain | PASS | Буквальных незакрытых markers нет; смысловые замечания к новому сценарию устранены, неизвестное runtime не подменено допущением. |
| RQ06: Requirements are testable and unambiguous | PASS | Финальный scenario8 определяет families/source/spoof/SNI/Host/stages/FD/sample/p95; исходные SC имеют числа и контракты. |
| RQ07: Success criteria are measurable | PASS | SC001–013: coverage0, IDs0, events0afterrefusal,100%campaign,test consistency,15min,30days,history/deletion,5R20min,approval truth. |
| RQ08: Success criteria are technology-agnostic (no implementation details) | PASS | SC задают измеряемое поведение и результат; выбор nginx/PROXY/таблиц и стадий в техническом плане. |
| RQ09: All acceptance scenarios are defined | PASS | US1–5, scenario1–8, T118 дополнение и contracts включают positive/negative/unknown/rollback, actual special отдельно от HTTPS fixture. |
| RQ10: Edge cases are identified | PASS | Consent corruption, unknown attribution, duplicates, loss/outage, storage/backup/restore, old worker late connect, SNI/Host bypass и IPv6 unknown определены. |
| RQ11: Scope is clearly bounded | PASS | F273/T098/7698; existing nginx1.24, без новых служб/ядра/зависимостей, соседи не редактируются автоматически, IP/provider не включаются. |
| RQ12: Dependencies and assumptions identified | PASS | 093/094/096, existing common stream/includes/manual installers/Compose/ASGI, exact peer, operator approvals/T097/T110/T118/T119 и release gates названы. |
| RQ13: All functional requirements have clear acceptance criteria | PASS | FR сгруппированы по US и связаны с SC/contracts/quickstart; новые FR061/062 имеют полную scenario8 и отдельную модель/writer gate. |
| RQ14: User scenarios cover primary flows | PASS | Все5US плюс native и browser-upload ветви, consent/revisit, acquisition/handoff, degraded/restore и launch covered. |
| RQ15: Feature meets measurable outcomes defined in Success Criteria | PASS | Проверена достаточность требований для проверки outcomes по карте ниже; выполнение outcomes, тесты и коммерческий рост не заявлены. |
| RQ16: No implementation details leak into specification | PASS | FR/SC — пользовательские/безопасностные границы; фиксированные названия существующих контрактов и legacy exception не подменяют технический план. |

## Связь критериев результата с требованиями

| SC | FR и контракт проверки |
| --- | --- |
| SC-001 | FR-009/011/058; anonymous-aggregate; scenario1 |
| SC-002 | FR-007/008/010/057; data-model/aggregate, actual stored rows |
| SC-003 | FR-012/042; reports R11 и caveats |
| SC-004 | FR-001/002/003/059; scenario5 и repeated visit |
| SC-005 | FR-014/015/017/018; handoff, scenario2/3 |
| SC-006 | FR-019–025; activation catalog и обе ветви scenario4 |
| SC-007 | FR-041/043; reports R07/R08, spend join |
| SC-008 | FR-017/024; reports consistency и разрешённый сопоставимый охват |
| SC-009 | FR-030/054–056; independent observer и scenario6 |
| SC-010 | FR-033–035/051–053; operations T118 и scenario7 |
| SC-011 | FR-036/039/048/050/061; отдельные retention/eligibility/deletion/capacity/IP gates |
| SC-012 | FR-031/032/039; operations «Нагрузка сайта» и scenario6 |
| SC-013 | FR-044–047; approval records/согласованность/rollback отдельно от flags |

## Что остаётся обязательным после этого PASS

- Анализ согласованности и синхронизация T098/#7698 до реализации; затем
  независимое ревью кода, профильные проверки, convergence, exact-SHA PR checks,
  общий Full/CD и штатная рабочая приёмка. Никаких этих результатов отчёт не даёт.
- Полный закрытый effective include graph и источник каждого listener;
  совпадение хешей перед применением, повторная проверка свободных портов,
  действующих параметров и новых доверенных сокетов. `nginx -t`/reload exit0
  без проверки реально обслуживающего поколения недостаточны.
- Действительные соседние vhost/cert/ALPN/HTTP2 и настоящий special-клиент;
  обе Docker-сети/host-network/local-users; проверка IPv4/IPv6 по отдельности.
  Отсутствие пути или полномочий — INCOMPLETE/BLOCK, не вымышленный PASS.
- Проверенный stage A/B/C/D и обратный переход с late ClientHello и дренированием;
  ≤15 минут наблюдения на стадию не разрешают kill чужих сессий. Оставшееся
  старое поколение/rec10444 блокирует приёмку. Исключение истекает 03.11.2026;
  истечение не разрешает принудительное удаление или молчаливое продление.
- Запрет ручных billing/share installers во время стадий; после перехода их
  согласованность с конечным rec-файлом. Direct8443 проверяется безопасными
  отказами, никакой оплаты ради ingress. Same-image exact-peer stage не меняет
  остальные флаги, зависимости и получателей.
- Ресурсная проба является изолированным инженерным критерием. Сообщённые
  исполнителем значения worker_connections=768 и soft FD=1024 не измеряют
  фактическое использование; этот проверяющий не принимал их рабочим доказательством.
  Нужны собственные полные замеры и T097 по исходному контракту 5×R.
- Настоящие writer→PostgreSQL→report и исключение оператора, suppression1–2
  до суммирования при пороге3; журналирование и получатели без нового raw IP.
  IP writer остаётся выключен до основания/опубликованного раскрытия/прав/
  аудита/GRAF DB backups по T110/T111. T118/T119/остальные readiness gates
  не отменены. Ни трафик, ни активация, ни продажа этим отчётом не доказаны.

## Итог перечитывания чек-листов

| Файл | Подтверждены | Открыты |
| --- | ---: | ---: |
| infra.md | 29 | 0 |
| security.md | 27 | 0 |
| privacy-measurement.md | 45 | 0 |
| requirements.md | 16 | 0 |
| Всего | 117 | 0 |

Новые infra CHK026–029 и security CHK026–027 подтверждены только после
оценки требований. Остальные 111 отметок независимо перепроверены и сохранены.
История прежних FAIL/PASS в чек-листах не удалена.

## Точные входные SHA-256

Таблица фиксирует содержимое финального прочитанного снимка; локальные
изменения не покрываются одним HEAD. Ниже нет хешей адресов посетителей.

| Файл | SHA-256 |
| --- | --- |
| `.specify/feature.json` | `ac8ed6f531fe255f2bde56ea358c33ac212ef63157f6178d57fe11f45ee0e1f2` |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/agent-guidance/release-and-validation.md` | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| `specs/273-paid-traffic-analytics/spec.md` | `7acca27029e038bcd32bc1aad3043b2ac01aaafd2bb3c9a3ff5fc710f1c0ceec` |
| `specs/273-paid-traffic-analytics/plan.md` | `d1020a471e778ed2a610fa8109bb4e46638d650c1a1041f68cbe0fe48d2d3ab2` |
| `specs/273-paid-traffic-analytics/research.md` | `fe08fce17ade22ad02505f1ba477c34ff87b41ed0b1392ae6f88eefe008ae957` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `9796fe22f6762cda227a9a62302398fdd129fc0b02b812a81af25bad26f09d0d` |
| `specs/273-paid-traffic-analytics/tasks.md` | `82fd15d7cde4df253f956f50b79a08376c7050821e71ac8d42fc4916aaff013c` |
| `specs/273-paid-traffic-analytics/data-model.md` | `4a8f615425e5448c391551bebe8128b729e4b60692ca40bfa3b62647a678151f` |
| `specs/273-paid-traffic-analytics/legal-basis.md` | `f5c8b5ea1bb2a145f438069dc64b0e3816fb46496de86aecd17d02d47db3d423` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `9cbd4fc9851f26ac676b92d1549e8f1a9bf02648d977f3382de6e03a04563759` |
| `specs/273-paid-traffic-analytics/contracts/anonymous-aggregate.md` | `7e10a25d64c9d94951bec8440c1c84d205e5bfc0e87f31364f0739c5357ca47f` |
| `specs/273-paid-traffic-analytics/contracts/attribution-handoff.md` | `8d5808a1bd4a1bbc6fbdbbc8cf1d301e246dd8822c25e841bef7ceaca723fd82` |
| `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` | `ba2e86a4034a348f09f1809deac7b6e47f2e92d0152069324bc3fb0400eabbaa` |
| `docs/analytics/product-activation-analytics.md` | `570fdc8b622f68427b93a8926e8be90fd04eed75785de4a470cfa2d479b4b040` |
| `docs/analytics/product-analytics-posthog-runbook.md` | `590417ae45d8f9f04443cd08510990dd65d46792c5ce3773e979b4832a1c7455` |
| `docs/analytics/product-analytics-capacity-baseline.md` | `2c4adb30a642aa9b0750e3932faaf45ec3b4537b5b0d694e7693e60218da8fb6` |
| `docs/analytics/product-analytics-provider-rollback.md` | `4048a73de064ae98987b675ff9c74ec5d35211ad887bfe3d074df88ba2d06e48` |
| `docs/analytics/product-analytics-legal-basis-records.md` | `8c12f85eb40bb2e59342ccdb2838a1abcf955919af5d710f3e8461e03c4dc1d4` |
| `docs/analytics/product-analytics-reports.md` | `0145f5260da04c29769093b79d295c67e97fdb6146370f823ce875a229accce3` |
| `infra/posthog/backup-restore.md` | `78c85de4d1a4e98d8d2597cea1dd4a85371de70115e0fda2ce477d3eabc022ad` |
| `specs/273-paid-traffic-analytics/validation/t098-ingress-design-review-2026-10-27.md` | `0d2cccaa25e1d5e998e23c905d09119828080dce62a51c5dda9e4a562e989e87` |

После изменения и перечитывания чек-листов повторно проверены **29/29**
SHA-256 таблицы и **7/7** якорей scoped-разрешения: расхождений нет.
Проверены последовательность/уникальность ID и матрица **117** отдельных
подтверждений; итоговые отметки **117 checked / 0 unchecked**.
`git diff --check` завершился с кодом0. Только Markdown/metadata проверки;
исполняемые и рабочие тесты не запускались. Хеш самого отчёта и финальных
чек-листов возвращается основному исполнителю отдельно, чтобы не создавать
самоссылочный digest.
