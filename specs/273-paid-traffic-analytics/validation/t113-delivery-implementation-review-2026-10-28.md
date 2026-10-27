# Независимое ревью реализации доставки T113/T106 — 28.10.2026

**Scoped PASS. Открытых блокирующих дефектов в проверенном срезе нет.**
Проверена несохранённая реализация поверх HEAD
`2968b175d13b1d4132178c12ae54e6010731afd2`, ветка
`codex/273-activation-delivery`. Это приёмка конкретного dirty diff, связанного
хешами ниже; один HEAD не определяет эти ещё не закоммиченные байты.

Проверяющий: `/root/activation_requirements_gate`. Lane: активный high-risk
Spec Kit срез F273/T113/T106. Исходный before-code gate —
`t113-delivery-before-code-2026-10-28.md`, 117 checked / 0 unchecked.
Чеклисты не изменялись; их качество требований не выдано за исполнение задач.

## Область и метод

Прочитан полный diff пяти исходных production-файлов: milestones,
posthog_client, router, yandex_offline, maintenance_worker; затем полностью
проверено добавленное исправление account_closure и его реальные вызывающие
пути. Прочитаны новый contract test и изменение unit-теста maintenance worker.
Применимые зависимости: текущий activation contract, before-code matrix,
существующая модель/миграция0106, session/tenant context, legal/provider gates,
AdvertisingTransferDecision, account-close finalization/fanout и существующие
ledger/ingress tests. Fragment прочитан на согласованность ограничений.

Использовано разрешённое владельцем повторное чтение затронутых требований
F273 и сверка остальных ранее прочитанных документов. Mandatory manifest
проверен самостоятельно: **9/9 совпали**. Это проверка содержимого документов,
а не доказательство полной продуктовой приёмки.

Проверяющий не запускал новые тесты или провайдерную сеть. Прочитан полный
итог последнего профильного запуска основного исполнителя, включая collection,
warnings, результаты и cleanup. Собственная команда `git diff --check` — PASS.
Единственная запись проверяющего — этот отчёт; код, spec/plan/tasks,
checklists, Git/GitHub, чаты, рабочие данные, release/deploy не изменялись.

## Найденные дефекты и повторная проверка исправлений

Все перечисленные ниже замечания переданы исполнителю и исправлены им до
текущей приёмки. Текущие строки относятся к финальному проверенному diff.

| ID | Важность | Проблема до исправления | Финальное доказательство |
| --- | --- | --- | --- |
| R01 | HIGH, закрыто | Любой запрещённый Yandex transfer превращался в терминальный purpose_withdrawn, включая временно отсутствующее основание или устаревшее раскрытие. Это теряло ранее принятое намерение без доказанного отзыва. | router.py:85–92 отменяет только три явных revoked/refusal blocker; остальные дают basis_unavailable → pending. Пять параметров test_fresh_advertising_decision_changes_only_yandex используют настоящий AdvertisingTransferDecision после подготовки секрета: явные отзывы отменяют только Yandex, unknown сохраняет pending; PostHog submitted. |
| R02 | MEDIUM, закрыто | provider gate добавляет legal_basis_withdrawn также при ошибках файла. Одна эта строка могла ошибочно отменить намерение, если файл стал нечитаем между двумя свежими проверками. | router.py:80 требует действительную запись withdrawal для нужного level_key; иначе basis_unavailable. test_provider_register_error_is_not_proof_of_withdrawal использует реальный BasisWithdrawalRegister с file_errors, со/без настоящего BasisWithdrawal. |
| R03 | HIGH, закрыто | До fanout закрытия аккаунта identity.status=closed коммитился отдельно, а ledger удалялся позже. Проверка только существования ledger могла разрешить отправку из закрытого аккаунта при долгом/упавшем fanout. | account_closure.py:204–217 в той же транзакции отменяет pending/pre_send_retry/dispatching обоих получателей только этого аккаунта. Реальный maintenance-login test выполняет begin дважды, коммитит без fanout/purge, проверяет оба cancelled, other-account pending, отказ свежего транспорта и false позднего finish. Submitted/ambiguous/confirmed не меняются. |

Отдельно проверено исправление прежней ошибки классификации PermissionError:
оно наследуется от OSError, которое перехватывают существующие wrappers.
router.py:127–142 сохраняет pre_send_blocker до исключения; строки163–164
возвращают его после wrapper catch. Свежий явный отказ поэтому не становится
неоднозначным сетевым исходом. Два параметра свежего level2 gate прошли в V5.

## Проверенные границы D01–D15

| Граница | Источник и наблюдение | Вывод |
| --- | --- | --- |
| 20 строк всего | router.py:198–214: один общий limit20 по двум fixed intents и stale, затем scoped quarantine этих IDs. test_scan_bound_and_no_hidden_backfill:23 записи→20+3; not_requested получатель не достраивается. | PASS |
| Один активный запрос получателю между процессами | milestones.py:368–394: короткая provider-specific advisory transaction, проверка общего dispatching и conditional claim. Состояние/attempt коммитятся до транспорта. Два одновременных worker с разными строками не отправляют вторую до освобождения первого. | PASS |
| Нет SQL-lock/транзакции во время HTTP | router.py:217–221 завершает claim commit до _deliver_claim; fresh read session закрыта до сетевого await. Во время заблокированного fake HTTP другая DB connection успешно обновляет claimed row. | PASS |
| ≤5 секунд и доступность event loop | guarded_transport имеет asyncio.timeout5; native httpx stream дополнительно ограничен min(timeout,5), redirects выключены. Wrappers работают в to_thread. Реальный зависающий async fake отменён примерно за5с, heartbeat продолжал работу, исход ambiguous, повторной отправки нет. | PASS |
| Пауза60 секунд и существующий процесс | maintenance_worker.py:49/160–173 подключает отдельную coroutine существующего maintenance процесса независимо от Temporal. После ошибки sleep60, ограниченный error_type вместо exception detail, dispose при отмене. Unit-тест подтверждает вызовы и disabled branch. | PASS |
| Свежие разрешения у фактического транспорта | router.py:126–145 после подготовки wrapper заново проверяет actual DB role, актуальные state/attempt, затем strict level2/recovery, provider gate и рекламное разрешение. Нет сети при withdrawn/unknown/disabled или утрате строки/попытки. | PASS |
| Доказанный pre-send и неопределённый сетевой исход | До transport доказанная configuration ошибка даёт pre_send_retry с прежним event_id; после входа timeout/OSError/429/500/400 дают ambiguous. Старое retryable не используется для решения о повторе. | PASS |
| Unknown commit и crash | Claim commit обязан завершиться до _deliver_claim; потерянный результат commit не даёт сети. Неподтверждённый finish оставляет dispatching, stale→ambiguous; последующий проход не пересылает. Три fault-параметра покрыты. | PASS |
| Независимые получатели | Завершение ограничено provider+id+attempt+dispatching; сбой PostHog не меняет успешный Yandex. Ожидающее намерение одного не создаёт новое у второго. | PASS |
| Отмена await | shield дожидается реального ограниченного транспорта и не освобождает durable слот как pending. Отмена тестового task не позволила второму worker отправить дубль; прерванный dispatching остаётся для карантина. | PASS |
| Удаление/закрытие аккаунта | Удалённая строка останавливает fresh check, finish не вставляет строку обратно. Атомарная отмена R03 закрывает durable окно до account fanout. Существующие ledger tests дополнительно проверяют точный account purge и запрет late admission. | PASS |
| Настоящая RLS роль | _require_delivery_database требует session_user=current_user=twobrain_rec_maintenance, row_security=on, NOSUPERUSER/NOBYPASSRLS, нужные operation/feature. Тесты фактических login принимают maintenance и отвергают app, superuser, неверный контекст и BYPASSRLS. | PASS |
| Допустимое содержимое и идентичность | Повторный build_activation_event и проверка серверного псевдонима выполняются до HTTP. Corrupt detached snapshot отклонён; immutable DB trigger сохранён. Source_kind/raw account не добавлены наружу. | PASS |
| Устойчивый event_id | Ledger UUID передаётся как PostHog uuid и Yandex PurchaseId; wrappers проверяют тип UUID. Тесты сравнивают точные байты с исходным event_id, прежний safe_payload и единственный локальный счёт; raw account отсутствует в отправленных телах. | PASS |
| Restart/restore | Выборка допускает лишь pending/pre_send_retry и stale для карантина. submitted/ambiguous/confirmed/cancelled/rejected/not_requested не пересылаются. Существующий restore ledger test прошёл; activation_recovery_unverified сохранён и отдельно проверен как блокирующий сеть. | PASS изолированной границы; реальное восстановление не принято |
| HTTP2xx и подтверждение чтением | http_accepted переводится только в submitted. Нет нового перехода confirmed или заполнения confirmation_ref по ответу HTTP; test_delivery_keeps_one_decision_and_never_confirms_from_2xx это проверяет. | PASS отрицательной границы; D16 открыт |

## Результаты проверок

Финальный запуск **V5**, журнал
`.dev/growth/t113-delivery-focused-v5-20261028.log`:

- collection_count=98;
- collection_digest=`c8b2829b4449ad9b8005c320ac69cdd83bd040edcb8fd17c4de05982cc80345a`;
- **98 passed, 2 warnings in42.60s**, runner46s;
- postgres_test_phase=focused status=pass;
- postgres_test_cleanup=isolated_container_removed;
- postgres_test_result=pass mode=focused partitioned=false shard=none.

Два предупреждения касаются pytest assertion rewriting и Starlette/httpx;
они не подменяют проваленный тест и не названы доказательством рабочего запуска.
Исторический V3:78 PASS; V4:85 PASS/2 FAIL — не итоговая приёмка. V4 выявил
ошибки самих добавленных тестов: попытку изменить защищённый immutable payload
и зависимость от пустого caplog. В V5 unsafe проверяется на detached snapshot,
logger проверяется через mock фактического вызова; SQL trigger не ослаблен.

## Точные байты проверенного среза

| Файл | SHA-256 |
| --- | --- |
| apps/server/src/twobrain_rec_server/auth/account_closure.py | 4100068fcfe0c993b2448fd81f5bb68f57c087f04f49c5cc979643d29249dd25 |
| apps/server/src/twobrain_rec_server/product_analytics/milestones.py | b9d6e1de6b80c128af3efd7d23b731e38486f6855fdf7f6fa3750af4bf33e0c6 |
| apps/server/src/twobrain_rec_server/product_analytics/router.py | 81f8bbb9eae28ee486e0da2a4857c654d98d988cc1d728227b2b8c459cef945a |
| apps/server/src/twobrain_rec_server/product_analytics/posthog_client.py | 12b49bb9d0eda5731091faf50dcc8ef770d6e1c90bc1a542353d0e7174ca4e5f |
| apps/server/src/twobrain_rec_server/product_analytics/yandex_offline.py | 6fda35950fbe613bac52400711af63bd283b40a1d86b843e0161f6a05e81c013 |
| apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py | 8e5ae2d4928f732a784cefabbf7da42b2b9435d7e668a091963ff335a10c1417 |
| apps/server/tests/contract/test_activation_milestone_delivery.py | 703f55ee2c71880fc42524b66b2a11d15aaba71c064dd3bacc1d3daf9faf5b64 |
| apps/server/tests/unit/test_maintenance_worker.py | b6749f42957bc0a8c1fa3b59a6b023436a8f0cdec9ae2a9554e7db99fe9109da |
| .dev/growth/t113-delivery-focused-v5-20261028.log | 38a9937774bbed6919c2ba3694bafdada83d583fc01cbd3ea61def154772a981 |

## Что остаётся открытым

Положительное точное readback-подтверждение D16 и завершение T113;
подключение настоящих T112-триггеров; T106 остальных writers; настоящие
GRAF DB backup/restore/reconciliation, удаление после restore и рабочие
T098/T109–T111/T116/T118/T119; точные SHA GitHub checks, merge, frozen candidate,
release-full и deploy. Этот отчёт не подтверждает трафик, регистрации,
активации, оплаты либо достижение коммерческих AC.

Рабочая аналитика/IP и provider delivery не включались. Существующий
безусловный activation_recovery_unverified не снят. Отправленный запрос и
принятый HTTP-ответ не объявлены прочитанным событием; уже начатая передача
не объявлена отменённой задним числом после закрытия аккаунта.

## Дополнительная проверка FR-049 и итог V6 — 28.10.2026

**Актуальный вердикт: scoped PASS исправления R04 и полного выбранного набора
V6. Открытых блокирующих замечаний в повторно проверенном срезе нет.**
Предыдущие разделы и хеши V5 сохранены как историческая запись: они не
описывают изменённые ниже байты. Исходный V5 PASS пропустил описанный здесь
дефект и до его исправления не мог разрешать слияние версии700df982.

Основной исполнитель обнаружил несоответствие идентификаторов до merge;
независимая дополнительная проверка подтвердила его по реальным вызовам и
читателю реестра. R04 — **HIGH, закрыто после исправления и V6**:

- `export(event,event_id=ledgerUUID)` менял PurchaseId на str(UUID), но
  `transfer_decision` и свежие dispatcher-проверки искали прежний hash события.
- `TRANSFER_REF_PATTERN` принимает только буквы/цифры/underscore; дефисы UUID
  делали реально отправляемую ссылку непригодной для точного refusal record.
  Читатель превращал такую reference в пустую, не снимая прочие основания.
- Поэтому точный запрет одной передачи мог не сработать при допустимых
  остальных основаниях. Это локальный дефект FR-049; никаких выводов о
  поведении Яндекса для доказательства не требуется.

Регрессионный unit-тест основного исполнителя до исправления действительно
упал: ожидалось0 обращений к fake transport, получено1. Прочитан журнал
`.dev/growth/t113-yandex-ref-regression-20261028.log`; это учебные данные и
подменённый транспорт, реальной отправки не было.

### Проверенное минимальное исправление

`yandex_offline.py:168–184` расширяет существующий
`yandex_offline_transfer_ref` необязательным проверенным UUID. Для ledger-пути
он даёт `graf_yandex_dedupe_{event_id.hex}`: неприватный устойчивый идентификатор
в прежней допустимой форме. Новый реестр, framework и расширение regexp не
добавлены. Вызовы без ledger ID сохраняют существующее вычисление.

Тот же helper задаёт `row.dedupe_key`/CSV PurchaseId (строка334),
`transfer_decision` (строка311), отказные metadata и проверку export (строка347).
Оба вызова `_delivery_blocker` в `_deliver_claim` передают именно row.event_id,
включая последний вызов после подготовки секрета непосредственно перед HTTP.
Следовательно reader и разрешение проверяют ту же ссылку, которую получит CSV.

Admission в ingest по-прежнему может предварительно проверять событие без
ledger ID. Этот путь не отправляет его наружу; последующий dispatcher всё
равно выполняет обе точные проверки с сохранённым ID. Принятие локального
решения не выдаётся за разрешение сетевой передачи, обхода здесь не найдено.

Два новых теста проверены по коду и финальному результату:

1. `test_product_analytics_yandex_offline_provider.py:454` создаёт настоящий
   file register с refusal по будущему точному PurchaseId, открывает его через
   from_settings, проверяет0 сетевых обращений, recipient_revoked и точный
   blocker/reference. Другой UUID не блокируется этим record и отправляет
   ожидаемую собственную reference в fake CSV.
2. `test_activation_milestone_delivery.py:306` восстанавливает настоящий
   transfer_decision и file reader. Запрет записывается после чтения секрета,
   поэтому прежний snapshot разрешения недостаточен. Свежий dispatcher
   переоткрывает реестр, не вызывает fake transport, сохраняет cancelled /
   purpose_withdrawn. Подставлены лишь учебное раскрытие и granted consent;
   это изолированный тест, рабочего обхода разрешений не введено.

Новый идентификатор в PurchaseId — способ локально сопоставить передаваемые
данные и точный запрет. Ни название существующего поля dedupe_key, ни этот
тест не доказывают внешнюю дедупликацию, идемпотентность или readback Яндекса.
Устойчивость местного счёта обеспечивается ledger; ambiguous по-прежнему не
пересылается автоматически, confirmed без отдельного чтения не выставляется.

### Финальная проверка V6 и текущие хеши

Проверяется dirty diff поверх
`700df982d03450f3412b3af3e4fa9416deb74cad`, ветка
`codex/273-activation-delivery`; это ещё не SHA исправляющего коммита.
Прочитан финальный журнал
`.dev/growth/t113-delivery-focused-v6-20261028.log`:
**100 passed, 2 warnings in43.02s**, runner46s, status=pass,
isolated_container_removed, partitioned=false / shard=none.
Collection100, digest
`2351f31f37c8a8ed071b046a31fa4aab2cea1cdee45f2ca2c28cc3b003672a10`.
Проверяющий заново тесты не запускал; самостоятельно повторил
`git diff --check` — PASS.

| Изменённый вход или новый журнал | Актуальный SHA-256 |
| --- | --- |
| apps/server/src/twobrain_rec_server/product_analytics/router.py | 4ac4c9b8ef50922becf396ac0a27ec3c0d776d2eaf6ec5a96f259b3ec23a21e5 |
| apps/server/src/twobrain_rec_server/product_analytics/yandex_offline.py | 2b982d134e1630e9d092ab86f07c9fefba1e147ef95c541d637c46f99d48f637 |
| apps/server/tests/contract/test_activation_milestone_delivery.py | 8d44952731f4753563ecbf5fd812fc348dc042116855d4b6f035d7dee24356b0 |
| apps/server/tests/unit/test_product_analytics_yandex_offline_provider.py | eadbb383aca00a25592ed18240ad9e84b1e025777fa169f0dc2836b571bf612a |
| .dev/growth/t113-yandex-ref-regression-20261028.log | 758fea8a63266a0645706e4be467204e647c037cad820694ff533a691c0e6266 |
| .dev/growth/t113-delivery-focused-v6-20261028.log | d79b02300195374a13270b010ca3b84e5e957224f8adb917c01769a2395380a6 |

Хеши остальных ранее проверенных production-файлов и worker unit-теста не
изменились. Исправление локальное; рабочее включение, полное восстановление,
T112, положительный D16, точные PR/GitHub/merge/release/production gates и
коммерческие результаты остаются открытыми. В дополнительном назначении
изменён только этот отчёт; код, спецификации, задачи, checklists, Git/GitHub,
другие чаты и рабочие данные проверяющий не менял.
