# Feature Specification: Личный кабинет, тарифы и биллинг

**Feature Branch**: `codex/140-user-account-billing`

**Created**: 2026-08-06

**Status**: Planned; implementation not started

**Input**: Пользователь просит спроектировать и зафиксировать готовый к публичному запуску личный кабинет GRAF: аккаунт, IA/UX/UI/CX, тарифы, оплату через YooKassa, подписки, платежи, чеки, возвраты, промокоды и реферальную систему; изучить Krisp и сопоставимые продукты, практики и тренды 2026 года; затем перепроверить полноту.

## Scope Summary

Feature 140 превращает существующий авторизованный кабинет GRAF в самостоятельный публичный account-and-billing контур. Он добавляет:

- персональное рабочее пространство для каждого нового самостоятельного пользователя;
- профиль, способы входа, активные сессии и устройства, уведомления, тему, язык и закрытие аккаунта;
- понятный обзор тарифа, фактического использования, хранения, даты и суммы следующего списания;
- первую публичную тарифную модель `Free` + `Личный` с помесячной и годовой оплатой;
- hosted-оплату и автопродление через YooKassa без передачи реквизитов карты в GRAF;
- управление способом оплаты, автопродлением, немедленным переходом на `Free` при неуспешном продлении, платежами, чеками и статической email-инструкцией для внешнего backoffice-возврата;
- персональный лимит server-owned хранения и co-termed платное расширение хранилища;
- серверные промокоды и реферальную программу без денежных выплат;
- операционную сверку, финансовый audit trail, уведомления и launch gates.

Feature не меняет capture safety: ручная локальная запись, видимый индикатор и одношаговый Stop никогда не зависят от тарифа или платежного статуса. Коммерческие ограничения могут управлять только новыми server-owned загрузкой, обработкой, хранением сверх бесплатного лимита и платными AI-возможностями.

## Product Decisions

- Billing subject — workspace. Самостоятельная регистрация создаёт отдельное личное workspace с одним Owner внутри общей SaaS auth Organization; Organization служит identity namespace, но не общей tenant/workspace. Приглашённый пользователь может переключаться на другое workspace той же Organization после membership recheck/session rotation.
- Платёжные действия доступны только активному Owner соответствующего workspace. Admin видит тариф и агрегированное использование без платёжного метода и реквизитов; Member видит доступные возможности и своё использование без финансовых данных.
- Первый публичный каталог содержит `Free` и `Личный`; enterprise/team sales-assisted остаётся вне self-service. Recommended launch catalog: `Free` = 300 server-processing minutes per calendar month, reset at day 1 `00:00 Europe/Moscow` with no rollover, + 250 MB playback archive; Trial = 500 MB; `Личный` = 790 ₽/month or 7 900 ₽/year + 2 GB. One co-termed add-on selects total capacity 5/20/100/500 GB. Decimal units are authoritative (`1 MB = 1 000 000 bytes`, `1 GB = 1 000 000 000 bytes`). Base price/capacities are publishable versioned hypotheses; add-on prices require a new COGS/value study and every checkout remains default-off until product, unit-economics, finance, accounting and legal approval.
- Free processing enforcement uses `18 000` seconds per window. Admission reserves declared media duration; only unique successfully accepted processed ranges commit their exact whole seconds. Failed/canceled/rejected ranges release reservation, partial success commits only its confirmed range, and per-meeting rounding is prohibited.
- Every successful saved capture package contains `manifest.json`, normalized `meeting-review.m4a` for playback and one normalized `meeting-transcription.wav` for transcription; a failed capture MAY contain only its manifest and failure truth. The transcription source is a mono 16 kHz PCM Int16 canonical mix at approximately 115.2 MB/hour. Measured playback objects are approximately 29.4 MB/hour on average (observed 28.5–30.7 MB/hour), so the measured audio-artifact footprint is approximately 144.6 MB/hour before replicas/backups and metadata. Customer storage quota counts only exact active `meeting-review.m4a` object bytes. Thus 250 MB ≈ 8.5 h, 500 MB ≈ 17.0 h and 2 GB ≈ 68.1 h of playback at the measured average; these hour values are disclosed estimates, never enforcement authority. Internal `meeting-transcription.wav` does not consume customer quota, MUST remain lifecycle-accounted, and MUST be purged after successful transcript import plus verified stored playback according to an approved source-retention policy; missing/failed verification retains a recoverable source under that policy rather than deleting silently.
- Self-service checkout доступен только личному workspace с одним billing Owner. При утрате Owner-роли будущие списания немедленно запрещаются; новый Owner заново принимает recurring terms и привязывает собственный способ оплаты — сохранённый метод не передаётся.
- `Личный` поддерживает месяц и год. После регистрации действует `Free`; eligible пользователь сам запускает пробный период кнопкой `Начать 7 дней бесплатно`. Trial доступен ровно один раз на verified `UserIdentity` независимо от числа personal workspaces и linked login methods, не требует карты/recurring consent; окончание переводит пользователя на `Free`, а не запускает скрытое списание.
- `Личный` не имеет коммерческого лимита по минутам, количеству встреч, транскрипциям и AI-заметкам. Хранение остаётся конечным; технические ограничения размера файла, concurrency, rate limits, safety и versioned fair-use policy не являются оплачиваемым overage и не снимаются покупкой.
- Заполненный архив не блокирует уже доступный processing entitlement: `Free`, Trial and `Личный` могут явно выбрать `Обработать без сохранения аудио`. На `Free` accepted seconds расходуют текущие 18 000 seconds; Trial/`Личный` не имеют commercial processing counter. GRAF временно держит media только на время server processing, сохраняет транскрипт/заметки, purges media within 15 minutes after terminal success/failure and enforces a hard 24-hour lifetime from admission even after a stuck job/worker crash. Постоянное сохранение нового audio остаётся заблокированным до освобождения или расширения storage.
- Fair-use не является расплывчатым правом отключить активного пользователя за объём. Он применяется только к автоматизированной массовой обработке, перепродаже/предоставлению сервиса третьим лицам, обходу технических ограничений или иной доказуемой неперсональной эксплуатации; обычное личное число встреч само по себе не является нарушением. Ограничение всегда называет capability/reason/review deadline и даёт appeal, а локальная запись, существующие данные, export/delete остаются доступны.
- Публичный launch не включает usage overage, авто-пополнение, платные пакеты AI-кредитов, stacking нескольких storage add-ons или seat-proration. Разрешён ровно один co-termed storage add-on, который меняет итоговую ёмкость личного workspace.
- Реферальная награда — не деньги: launch campaign gives invited user 10% off first paid period; inviter after maturity receives 7 calendar days for first monthly payment or 30 days for first annual. Cash payout, withdrawable balance and affiliate cabinet are excluded. Any changed percentage creates a new campaign version.
- Отмена автопродления, возврат платежа, закрытие аккаунта и удаление meeting data — разные процессы с разными последствиями; refund выполняется вне продукта, а product-side destructive/financial actions имеют отдельное подтверждение.
- Launch payment-method allowlist — `bank_card`; zero-amount binding и событие `payment_method.active` являются обязательной проверенной возможностью real shop. Неоднозначный small-payment/refund fallback не используется.
- Promo/referral не могут уменьшить сумму ниже утверждённого provider floor; zero-total checkout и 100% скидка исключены из launch.
- Публичный продукт не содержит refund workflow. Кабинет показывает только отдельный опубликованный refund/support email, безопасный номер платежа, предупреждение не отправлять данные карты/meeting content и действие `Написать письмо`. Письмо, рассмотрение, расчёт, решение и ручной возврат через merchant cabinet YooKassa являются backoffice-процессом вне GRAF; GRAF не создаёт refund case, не показывает статус/таймлайн, не рассчитывает сумму и не вызывает refund API. Чтобы немедленно остановить будущие списания, пользователь отдельно использует self-service `Отключить автопродление`; одно лишь письмо этого не делает. Backend observes only authoritative provider refund/receipt truth required for reconciliation and abuse-safe entitlement/referral accounting, without exposing a refund feature.
- Grace period, `past_due` и автоматические T+1/T+3/T+5 повторные списания исключены. GRAF делает одну renewal operation; confirmed failure или отсутствие подтверждённой оплаты к `paid_through` немедленно переводит workspace на `Free`. Transport recovery/poll той же unknown operation не является новой попыткой списания. Возобновление после final failure — только вручную с новым summary/consent.
- Downgrade сам по себе не удаляет meeting data: уже принятые сервером jobs завершаются за счёт заканчивающегося периода, новые uploads/paid jobs проверяют `Free`; непринятые desktop queues остаются локально до существующего 7-дневного срока. Дальнейшее удаление идёт только по существующей workspace retention policy.
- Account close launch cooling period — 7 суток по versioned policy. Future charges блокируются при scheduling; до `finalize_at` пользователь может отменить закрытие. Durable finalizer выполняется через Temporal и переживает restart/retry.

- После принятия удаления meeting или начала финализации account close нормальный recovery-retention срок transcription source больше не применяется: playback и все current/legacy transcription artifacts немедленно теряют доступ, освобождают customer quota where applicable и переходят в обязательный primary purge. Только formal mandatory hold с authority, reason, scope, timestamps, review/expiry and audit MAY отложить physical purge; если approved hold capability отсутствует на launch, такого исключения нет. Backups недоступны как пользовательское восстановление и истекают по опубликованной backup policy.

### Launch Tariff Levels

| Level | Commercial use | Storage | Billing | Product role |
|---|---|---|---|---|
| `Free` | 300 minutes/month server processing, no rollover; local Record/Stop always available | 250 MB playback archive (≈8.5 h at measured average) | 0 ₽, no method | знакомство и recovery after trial/paid cutoff |
| `Trial Личного` | same unlimited commercial dimensions as `Личный` for 7 days | 500 MB playback archive (≈17.0 h) | no card, no auto-charge | проверить full paid value without payment surprise |
| `Личный` | no commercial cap on meeting minutes/count, transcription and AI notes; disclosed technical/fair-use ceilings remain | 2 GB playback archive (≈68.1 h) | 790 ₽/month or 7 900 ₽/year; one automatic renewal operation | единственный self-service paid plan at launch |
| `Storage add-on` | does not change feature/usage entitlement | total 5/20/100/500 GB | versioned price schedule blocked pending COGS/value approval | расширить archive without inventing a duplicate paid tier |
| `Team/Enterprise` | not promised by feature 140 | sales-defined later | sales-assisted only | future slice after roles/seats/admin needs are proven |

The pricing page MUST compare these levels without presenting add-on as a separate base plan and label annual `Личный` as `2 месяца бесплатно` only while 7 900 ₽ remains exactly ten monthly prices. All numbers are recommended launch hypotheses, not hidden placeholders: changing any before approval creates a new catalog/offer version and re-runs checkout, receipt, COGS and usability gates.

Pre-purchase copy MUST place the finite archive boundary next to unlimited wording: `Без лимита по минутам и встречам. Включено 2 ГБ для playback-аудиоархива; при заполнении можно продолжить обработку без сохранения аудио или увеличить хранилище.`

## Clarifications

### Session 2026-08-06

- Q: Как должен запускаться бесплатный 7-дневный пробный период и сколько раз один пользователь может его получить? → A: По явной кнопке, один раз на verified UserIdentity.
- Q: Когда должен обновляться бесплатный лимит Free в 300 минут обработки? → A: Первого числа в 00:00 Europe/Moscow, без переноса остатка.
- Q: Как рассчитывать использованные минуты из лимита Free? → A: По точным успешно обработанным секундам, без округления каждой встречи.
- Q: На каких тарифах доступна обработка без сохранения аудио при заполненном архиве? → A: На всех; Free расходует quota seconds, Trial/Личный — без commercial counter.
- Q: Какую модель хранения и какие лимиты использовать с учётом реальных размеров GRAF-аудио? → A: Playback-only quota: Free 250 MB, Trial 500 MB, Личный 2 GB; add-on total 5/20/100/500 GB.
- Q: Что показывать пользователю, который ещё не подтвердил основную личность? → A: Trial заблокирован; показывать CTA подтверждения, после verification eligibility обновляется автоматически.
- Q: Что делать с playback и transcription audio после удаления встречи или финализации account close? → A: Сразу исключать из доступа/quota и отправлять все current/legacy primary artifacts в обязательный purge без recovery-retention ожидания; исключение — только формально зарегистрированный обязательный hold, backups истекают по опубликованной policy.
- Q: Через какой публичный канал пользователь запрашивает возврат? → A: Только письмом на отдельный refund/support email; кабинет показывает инструкцию и `Написать письмо`, но не содержит refund form и никогда автоматически не исполняет возврат.
- Q: Какой срок ответа обещать публично для refund email? → C: GRAF не обещает и не отслеживает SLA/status; acknowledgement, ответы и mandatory legal deadlines принадлежат внешнему support/merchant process.
- Q: Где рассчитывается, одобряется и исполняется возврат? → A: Полностью вне продукта: support email + ручной backoffice-процесс в merchant cabinet YooKassa; GRAF не имеет refund case/status/timeline/operator UI и только сверяет уже подтверждённый provider outcome внутри финансового контура.
- Фактический capture package перепроверен по manifest v5 из текущей установленной сборки: `manifest.json`, `meeting-review.m4a` и единственный `meeting-transcription.wav`; прежняя пара `mic.wav`/`incoming.wav` не является текущей моделью артефактов.
- Публичная SaaS-регистрация создаёт личное workspace в общей auth Organization; общая техническая workspace из текущего login flow не является tenant ownership. Multi-workspace доступ выполняется через явный membership-checked session switch, а multi-organization/global identity остаётся отдельным auth slice.
- YooKassa используется как payment processor и vault сохранённого способа оплаты, а GRAF владеет subscription schedule, invoice ledger, one-attempt renewal, promo/referral и entitlement truth.
- Hosted redirect выбран для launch вместо embedded card form: GRAF не получает PAN/CVC и активирует доступ только после server-side подтверждения успешного платежа.
- Биллинг и checkout являются browser-only поверхностями; desktop embedded кабинет показывает статус и открывает платёжные действия во внешнем браузере, сохраняя native Record/Stop.
- Launch catalogue ограничен `Free` + `Личный`; team self-service, usage overage, cash rewards, multiple billing providers и внутренний финансовый backoffice UI исключены.
- Один промокод или referral intro-discount может уменьшать первый invoice приглашённого; применяется наиболее выгодная допустимая скидка. Time credit пригласившего не уменьшает invoice и учитывается отдельным append-only ledger.
- Пригласивший получает 7 календарных суток за first-paid monthly и 30 суток за first-paid annual после 14-calendar-day maturity. Security review MAY pause maturity; authoritative provider-confirmed refund before maturity prevents reward, and a later confirmed refund follows bounded reversal. Credit привязан к personal workspace: у active с автопродлением он откладывает следующую renewal date, у cancel-scheduled продлевает только финальный service/add-on cutoff без создания charge job, у `Free` хранится до 12 месяцев и применяется после первой собственной оплаты. Launch cap — 180 начисленных суток на workspace за rolling 12 months; один referee создаёт одну награду.
- На `Личном` минуты, встречи, транскрипции и AI-заметки отображаются как `Без лимита` плюс фактическое использование без `remaining`. Хранение отображает used/reserved/available и остаётся единственным коммерческим расходуемым лимитом paid-плана.
- `Free` содержит 250 MB playback archive, Trial — 500 MB, `Личный` — 2 GB; add-on выбирает одну итоговую ёмкость 5/20/100/500 GB. Add-on co-termed с базовой подпиской: в initial checkout это отдельная строка; mid-cycle upgrade активируется после немедленной pro-rata оплаты положительной разницы до общей renewal date; downgrade/removal применяется на следующем renewal. При переходе на `Free` over-quota data не удаляется, но archival uploads блокируются до удаления данных или возобновления тарифа/add-on; no-archive processing remains available under plan processing entitlement.
- При confirmed renewal failure paid access заканчивается ровно в `paid_through`, повторных автоматических попыток нет. Pending/unknown operation после cutoff даёт `Free` плюс статус `Проверяем исход`; новый платёж блокирован. Late success без более раннего отказа восстанавливает полный оплаченный период от момента восстановления и сдвигает следующий anchor; late-after-refusal оставляет `Free` и открывает priority case, пока плательщик явно не выберет non-renewing paid period.
- Refund email и все ответы обрабатываются вне GRAF. Продукт не хранит обращение и не показывает его состояние; backoffice отвечает по email без собственного публичного SLA и вручную выполняет одобренный возврат в YooKassa. Отказ от будущих списаний остаётся отдельным self-service действием в кабинете и не выводится из свободного текста письма автоматически.
- Receipt contact для personal launch — verified primary login email, snapshot которого ограниченно хранится на invoice/payment; checkout показывает mask, но не позволяет подменить адрес. Изменение login email требует отдельного verified account flow.
- Daily YooKassa registry launch flow — audited manual import официального CSV оператором; hash+report date+part dedupe, Moscow-day cutoff, empty/missing/multipart handling и ограниченная retention обязательны. SFTP automation остаётся отдельным улучшением.

## Actors And Authority

- **Новый пользователь**: регистрируется, получает личное workspace и `Free`; до подтверждения основной личности trial недоступен и UI ведёт в verification flow, после которого eligibility обновляется автоматически; eligible verified пользователь может один раз явно запустить trial.
- **Workspace Owner / плательщик**: единственный billing Owner личного workspace выбирает тариф/add-on, принимает оферту и автоплатёж, управляет оплатой, промокодом и отменой; в истории видит опубликованный refund/support email и safe invoice reference для внешнего обращения. Его billing authority не передаётся вместе с сохранённым способом оплаты.
- **Workspace Admin**: видит тариф, общие лимиты и использование, но не видит сохранённый способ оплаты, чековый контакт или налоговые реквизиты и не может инициировать списание/возврат.
- **Workspace Member**: видит доступные возможности и своё использование без суммы, платежей и реквизитов.
- **Пригласивший / приглашённый**: участвуют в referral lifecycle с ограниченной видимостью друг друга.
- **Финансовый оператор GRAF**: вне продукта рассматривает refund email и вручную выполняет одобренный возврат в merchant cabinet YooKassa; внутри GRAF использует только audited reconciliation/correction runbook без refund case или superadmin UI.
- **YooKassa**: исполняет одну платёжную попытку, хранит платёжный метод и регистрирует чек в согласованном сценарии; не является subscription engine GRAF.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Создать личный аккаунт и безопасно управлять им (Priority: P1)

Новый пользователь регистрируется через существующий passwordless/provider flow, получает изолированное личное workspace и открывает account center. Он может изменить отображаемое имя, язык, часовой пояс и тему, просмотреть способы входа, активные сессии и устройства, отозвать чужую сессию, выйти везде и начать закрытие аккаунта с правдивым объяснением последствий.

**Why this priority**: Публичный биллинг нельзя привязать к общей технической workspace или неполному аккаунту; tenant ownership, безопасность и recovery должны быть истинными до первой оплаты.

**Independent Test**: Зарегистрировать нового пользователя, доказать создание отдельного workspace, изменить профиль, переключить тему, отозвать вторую сессию и пройти preview закрытия аккаунта без доступа к данным другой workspace.

**Acceptance Scenarios**:

1. **Given** новый email/provider identity не принадлежит GRAF, **When** пользователь завершает регистрацию, **Then** создаются отдельные user identity, личное workspace, Owner membership и `Free` entitlement без общей workspace с другими самостоятельными пользователями.
2. **Given** пользователь открыл меню аккаунта, **When** он выбирает профиль, безопасность, тариф, рефералов или выход, **Then** каждый пункт имеет один однозначный destination и корректный current/focus state.
3. **Given** у Owner две активные browser/desktop sessions, **When** он отзывает одну, **Then** отозванная сессия теряет доступ, текущая остаётся активной, а событие появляется в metadata-only audit.
4. **Given** пользователь закрывает аккаунт, **When** он читает preview, **Then** интерфейс отдельно показывает отмену будущих списаний, судьбу workspace memberships, meeting deletion/export, сроки финансовых записей и пределы данных у YooKassa.

---

### User Story 2 - Понять тариф и использование без сюрпризов (Priority: P1)

Пользователь видит текущий тариф, trial/subscription status, безлимитные paid-возможности, фактическое использование, storage used/reserved/available, add-on и дату следующего списания. Финансовая сумма показывается только Owner.

**Why this priority**: Пользователь должен понимать ценность и ограничения до покупки; quota UI не может расходиться с реальным entitlement enforcement.

**Independent Test**: Открыть один workspace как Owner, Admin и Member; проверить paid `Без лимита` без фиктивного remaining, storage 80/95/100% states, exact byte reconciliation и роль-зависимую видимость add-on/денег.

**Acceptance Scenarios**:

1. **Given** verified `UserIdentity` ещё не использовал trial и находится на `Free`, **When** Owner явно подтверждает `Начать 7 дней бесплатно`, **Then** один atomic activation включает trial на 7 дней без карты/recurring consent и фиксирует точные start/end timestamps.
2. **Given** тот же `UserIdentity` уже запускал trial, **When** он повторяет действие из другого workspace, linked login method, session или concurrent tab, **Then** новый trial не создаётся, состояние не изменяется и UI объясняет однократное правило без раскрытия risk signals.
3. **Given** активен trial, **When** Owner открывает account/billing overview, **Then** он видит оставшиеся дни, точную дату окончания, отсутствие автосписания и CTA выбора тарифа.
4. **Given** активен `Личный`, **When** пользователь открывает `Использование`, **Then** минуты/встречи/transcription/AI показываются как `Без лимита` и фактический объём без remaining/reset, а storage показывает exact used/reserved/available из 2 GB или активной 5/20/100/500 GB add-on capacity.
5. **Given** показатель устарел или ещё агрегируется, **When** он показан, **Then** интерфейс отмечает freshness и не выдаёт приблизительное значение за окончательный финансовый факт.
6. **Given** storage заполнен на `Free`, Trial или `Личном`, **When** пользователь продолжает локальную запись, **Then** Record/Stop и локальный файл работают; UI блокирует archival upload и предлагает на равных удалить server data, купить/увеличить add-on или явно `Обработать без сохранения аудио` с предупреждением об отсутствии последующего playback. Free path резервирует/коммитит quota seconds по FR-027; Trial/`Личный` не получают commercial counter.
7. **Given** paid use попал под fair-use review, **When** пользователь открывает кабинет, **Then** он видит affected capability, bounded reason, review deadline не позднее 24 часов и appeal/support action, while local Record/Stop and existing read/export/delete remain available.
8. **Given** `Free` quota window пересекает первое число, **When** наступает `00:00 Europe/Moscow`, **Then** новый 300-minute window создаётся ровно один раз, unused balance не переносится, concurrent accepted jobs относятся к window по authoritative acceptance timestamp, а UI показывает следующий reset в локальном часовом поясе пользователя с пометкой исходной зоны.
9. **Given** `Free` job завершился полностью, частично, с ошибкой, отменой или retry overlapping range, **When** usage ledger commits outcome, **Then** он добавляет только unique accepted whole seconds, releases every unaccepted reservation, never rounds a meeting upward and never counts the same source range twice.

---

### User Story 3 - Купить `Личный` через YooKassa (Priority: P1)

Owner выбирает месяц или год, при необходимости storage capacity, видит строки base/add-on, полную стоимость сегодня и следующего периода, скидку, правила trial/renewal/cancel, email-only refund boundary и versioned offer. После явного согласия он переходит на hosted YooKassa checkout и возвращается в GRAF, где видит проверяемый processing/success/failure state.

**Why this priority**: Первый платёж создаёт денежное обязательство и сохранённый способ оплаты; любые неясности приводят к двойным списаниям, чекам с неверной суммой и потере доверия.

**Independent Test**: В test shop пройти successful, abandoned, canceled и unknown-result flows, включая двойной click и повтор redirect, и доказать один invoice, одну logical operation и активацию только после подтверждённого provider success.

**Acceptance Scenarios**:

1. **Given** Owner выбрал `Личный` на месяц и storage capacity, **When** checkout summary открыт, **Then** он видит base/add-on lines, сумму сегодня, скидку, следующую дату/сумму, автопродление, отмену, email-only external refund boundary и действующую оферту до кнопки оплаты.
2. **Given** пользователь нажал `Оплатить в YooKassa`, **When** GRAF создаёт checkout, **Then** итоговая сумма, валюта, tariff version, discount snapshot и чековый состав вычислены server-side, а card fields не проходят через GRAF.
3. **Given** браузер вернулся по return URL, **When** provider status ещё не подтверждён, **Then** UI показывает `Проверяем оплату` и не активирует paid entitlement.
4. **Given** provider подтвердил успешную оплату и сохранённый способ, **When** GRAF применяет событие, **Then** invoice оплачен ровно один раз, подписка активна, entitlement обновлён, чек доступен, а следующая дата/сумма видимы.
5. **Given** платеж успешен, но метод не сохранён, **When** период активируется, **Then** текущий период доступен, а автопродление показывает `Нужно добавить способ оплаты` вместо ложного `включено`.

---

### User Story 4 - Управлять подпиской и способом оплаты (Priority: P1)

Owner меняет способ оплаты, отключает или возвращает автопродление, переключает месяц/год, покупает/увеличивает storage add-on с точным pro-rata preview и планирует уменьшение/удаление add-on на renewal. Базовые операции выполняются self-service без обращения в поддержку.

**Why this priority**: Публичная подписка без прозрачного self-service cancellation является неприемлемым CX и финансовым риском.

**Independent Test**: Заменить payment method, отключить renewal, включить снова до period end, сменить cycle и проверить, что каждая операция имеет preview, audit и не создаёт немедленное списание без явного подтверждения.

**Acceptance Scenarios**:

1. **Given** у подписки есть активный метод, **When** Owner выбирает `Изменить способ оплаты`, **Then** новая hosted-привязка проверяется до замены, а старый метод остаётся рабочим до успеха.
2. **Given** Owner выбирает `Отключить автопродление`, **When** он подтверждает действие, **Then** UI показывает точную дату окончания paid access, optional reason можно пропустить, будущие charge jobs запрещены, а текущий период сохраняется.
3. **Given** отмена запланирована, **When** Owner нажимает `Возобновить`, **Then** renewal возвращается только после подтверждения пригодного payment method и показывает следующую дату/сумму.
4. **Given** Owner меняет cycle или plan version, **When** preview открыт, **Then** он видит effective date, current credit/unused period treatment и точную сумму до подтверждения; скрытая proration запрещена.
5. **Given** Owner выбирает удаление способа, **When** renewal включён, **Then** guard ничего не удаляет и предлагает сначала отключить автопродление; на Free/renewal-off отдельное подтверждение удаляет method без изменения уже оплаченного периода.
6. **Given** Owner mid-cycle увеличивает storage capacity, **When** preview подтверждён, **Then** UI показывает положительную pro-rata разницу и общий renewal anchor; capacity меняется только после confirmed payment, а уменьшение/удаление применяется без скрытого refund на следующем renewal.

---

### User Story 5 - Понять немедленный переход на Free и восстановить подписку (Priority: P1)

При confirmed decline пользователь в `paid_through` сразу получает `Free`, без grace и повторных автоматических списаний. При unknown outcome UI честно сообщает, что paid-доступ не продлён, исход проверяется и новая оплата временно заблокирована. После final failure пользователь вручную запускает новое возобновление.

**Why this priority**: Renewal failure влияет на доступ и деньги; скрытый retry или платный grace создают дубли и непрозрачное обязательство.

**Independent Test**: Смоделировать confirmed decline, method failure, provider 500/429, webhook outage, late success и manual resume; проверить одну automatic operation, Free exactly at cutoff, same-key unknown recovery, no pay-again while unknown и полный новый период после late success.

**Acceptance Scenarios**:

1. **Given** renewal имеет confirmed `payment.canceled` или unusable method, **When** наступает `paid_through`, **Then** workspace немедленно получает `Free`, future retries отсутствуют, а CTA предлагает ручное `Возобновить Личный`.
2. **Given** provider вернул 500/timeout и исход неизвестен, **When** наступает cutoff, **Then** entitlement становится `Free` с derived status `Проверяем исход`; worker только читает/повторяет ту же operation/key, а новый payment CTA отсутствует.
3. **Given** unknown operation позднее подтверждена successful без более раннего effective refusal, **When** GRAF применяет authoritative truth, **Then** `Личный` восстанавливается ровно один раз на полный purchased period от `access_restored_at`, а следующий anchor сдвигается.
4. **Given** renewal окончательно не прошёл, **When** пользователь вручную возобновляет тариф, **Then** он получает fresh summary/consent/checkout и новый logical operation только после финализации предыдущего.
5. **Given** после downgrade storage выше 250 MB, **When** пользователь открывает данные, **Then** существующие meeting data доступны для чтения/export/delete, archival upload блокирован, no-archive processing follows plan quota, а автоматическое удаление не начинается.
6. **Given** пользователь раньше отключил renewal/отказался от payment data, **When** unknown payment позднее стал successful, **Then** workspace остаётся `Free`, recurring authority остаётся off, создаётся один internal financial incident без public case UI, пользователь получает email с support address, а возврат/иная коррекция решается backoffice вне продукта.

---

### User Story 6 - Найти платеж, чек и написать о возврате (Priority: P1)

Owner открывает историю с invoice/payment status, суммой, периодом и безопасным reference; получает электронный чек и статическую инструкцию написать на отдельный refund/support email. Публичный UI не содержит refund case, status/timeline, form, calculation или execution.

**Why this priority**: Деньги должны быть объяснимыми и сверяемыми; cancel не заменяет refund.

**Independent Test**: Проверить, что payment history показывает safe reference/email instruction, `Написать письмо` открывает внешний mail client без sensitive data, а GRAF routes/API/schema не создают public/internal refund-case workflow; отдельно доказать reconciliation уже совершённого в YooKassa provider refund/receipt без user-facing status.

**Acceptance Scenarios**:

1. **Given** invoice оплачен, **When** Owner открывает историю, **Then** он видит сумму, период, tariff/discount snapshot, безопасный номер, статус, чек и способ оплаты в маскированном виде.
2. **Given** Owner открывает refund instruction, **When** он выбирает `Написать письмо`, **Then** mail client получает опубликованный адрес, безопасную тему/reference и шаблон обязательных сведений без суммы, card data или meeting content; кабинет не создаёт provider mutation и отдельно предлагает отключить автопродление, если нужно остановить будущие списания.
3. **Given** support рассматривает письмо, **When** принимается решение, **Then** вся переписка/approval и исполнение проходят вне GRAF в support/backoffice и merchant cabinet YooKassa; в продукте не появляется case, status, timeline или operator control.
4. **Given** YooKassa уже подтверждает refund/receipt outcome, **When** reconciliation импортирует provider truth, **Then** internal finance/referral/entitlement projections сходятся идемпотентно без нового пользовательского refund surface или автоматической повторной выплаты.
5. **Given** финансовый документ должен храниться после закрытия аккаунта, **When** пользователь читает deletion copy, **Then** retention и доступ/выдача документа объяснены отдельно от meeting deletion.

---

### User Story 7 - Применить промокод без скрытых условий (Priority: P2)

Owner вводит промокод в checkout или `Скидки`, сразу видит eligibility, размер, применимый период, срок и следующую цену. Server атомарно резервирует и фиксирует redemption; клиент не вычисляет скидку.

**Why this priority**: Промо помогает acquisition, но stacking, races и неверные чековые суммы легко превращают его в financial abuse.

**Independent Test**: Проверить valid, expired, exhausted, ineligible, reused, concurrent и case-normalized codes, а также конфликт referral discount; итог invoice/receipt всегда совпадает с выбранным правилом.

**Acceptance Scenarios**:

1. **Given** допустимый код, **When** Owner нажимает `Применить`, **Then** summary показывает старую цену, скидку, итог сегодня, последующую обычную цену и срок действия.
2. **Given** promo и referral intro-discount одновременно допустимы, **When** checkout рассчитывается, **Then** применяется более выгодная одна скидка и UI называет отклонённую альтернативу; скрытое stacking запрещено.
3. **Given** код исчерпан между preview и оплатой, **When** invoice создаётся, **Then** операция не списывает неожиданную полную цену, а возвращает пользователя к обновлённому summary.
4. **Given** код недействителен, **When** пользователь получает ошибку, **Then** сообщение не раскрывает campaign internals или количество оставшихся активаций.

---

### User Story 8 - Пригласить друга и получить дни подписки (Priority: P2)

Пользователь получает opaque referral link, копирует его или отправляет приглашение. Приглашённый получает заявленную скидку на первый оплаченный период, а referrer после maturity — 7 суток за monthly или 30 суток за annual first payment. Награда продлевает service time, не имеет денежной стоимости и не влияет на invoice.

**Why this priority**: Рефералы могут снизить acquisition cost, но reward до доказанной ценности создаёт multi-account fraud.

**Independent Test**: Пройти attributed signup, first payment, maturity, reward, authoritative provider-confirmed refund reversal, self-referral, duplicate attribution и cap; ledger остаётся append-only и выдаёт ровно одну награду.

**Acceptance Scenarios**:

1. **Given** новый visitor открыл валидную referral link, **When** он регистрируется, **Then** first-touch attribution фиксируется один раз без передачи link token в analytics/logs и не перезаписывается позже.
2. **Given** referee впервые оплатил допустимый plan, **When** 14-day maturity ещё не закончился, **Then** reward имеет статус `Ожидает подтверждения` и не расходуется; само support email не влияет на state.
3. **Given** maturity пройден и authoritative provider-confirmed refund отсутствует, **When** reward становится available, **Then** referrer получает 7/30 calendar-day credit по cycle первого платежа, expiry/cap, notification и одну ledger entry.
4. **Given** payment/referral позднее отменён по authoritative provider-confirmed refund/abuse decision, **When** reward ещё не израсходован или частично израсходован, **Then** reversal отражается отдельной ledger entry и не создаёт отрицательный скрытый денежный долг.
5. **Given** anti-fraud сигнал сработал, **When** reward задержан или отклонён, **Then** UI показывает bounded reason class и appeal/support path без раскрытия detection logic.

---

### User Story 9 - Получать своевременные финансовые уведомления (Priority: P2)

Пользователь получает transactional уведомления о trial end, upcoming renewal, payment success/failure и немедленном Free, unknown resolution, cancel/resume, storage threshold/add-on и referral time credit. Refund correspondence остаётся вне продуктового notification outbox и идёт через support email. Marketing preference не может отключить обязательные security/financial notices.

**Why this priority**: Автосписание и потери доступа не должны быть неожиданными; уведомления являются частью consent и recovery.

**Independent Test**: Сгенерировать каждое событие дважды и доказать одно уведомление на idempotent key, корректную роль/язык, безопасный deep link и отсутствие provider token/meeting content.

**Acceptance Scenarios**:

1. **Given** renewal приближается, **When** notice window наступает, **Then** Owner получает дату, сумму, plan, payment-method mask и self-service link.
2. **Given** renewal confirmed failed, **When** `paid_through` наступил, **Then** уведомление говорит, что `Личный` закончился, workspace уже на `Free`, автоматических повторов не будет и возобновление запускается вручную.
3. **Given** пользователь отключил marketing, **When** происходит финансовое или security событие, **Then** обязательное transactional notice всё равно доставляется согласно policy.

---

### User Story 10 - Оперировать биллинг и доказать готовность к запуску (Priority: P1)

Финансовый оператор и release owner могут безопасно найти invoice/payment and observed provider-refund reconciliation truth, остановить future charges, сверить add-on/storage/time-credit и provider реестр, расследовать gap и доказать test/prod readiness без private evidence. Рассмотрение/approval/исполнение возврата остаётся в support/backoffice и merchant cabinet YooKassa вне GRAF.

**Why this priority**: Публичный payment flow нельзя запускать без reconciliation, emergency stop, поддержки и точного ownership.

**Independent Test**: Test shop E2E и real-shop canary проходят base+add-on payment → verified unlimited/storage entitlement → receipt → manual merchant-cabinet refund outside GRAF → observed refund/receipt registry reconciliation; GRAF не создаёт refund case/operator UI, а emergency disable не ломает кабинет.

**Acceptance Scenarios**:

1. **Given** webhook задержан или потерян, **When** poll/reconciliation запускается, **Then** confirmed provider truth сходится с internal ledger без двойного применения.
2. **Given** обнаружен финансовый incident, **When** оператор включает stop-all-charges, **Then** новые GRAF checkout/renewal/binding блокируются, while external support/refund backoffice, payment-data refusal, read-only history and cancellation remain available, а incident state видим support/release owner.
3. **Given** manually executed YooKassa refund or reward correction is observed, **When** reconciliation applies it, **Then** provider reference class, source, before/after и reconciliation note попадают в immutable metadata-only audit без refund-case content.

### Edge Cases

- Двойной click checkout, две вкладки, повтор return URL, два scheduler workers или race manual payment vs renewal.
- Webhook дублируется, приходит не по порядку, приходит спустя 24 часа, содержит неизвестный object id или относится к test shop в production.
- Payment succeeded, а способ не сохранён; метод expired/revoked/restricted; zero-amount binding недоступен в real shop.
- Provider 429, 500, timeout, partial network failure или недоступен checkout; исход операции известен/неизвестен.
- Invoice amount после promo/referral равен нулю, меньше provider minimum, требует округления или не совпадает с receipt items.
- Promo истёк во время checkout; исчерпан параллельным пользователем; меняется тарифная версия; код содержит смешанный регистр/Unicode/confusable characters.
- Self-referral, несколько аккаунтов, общий device/payment profile/domain/IP, быстрый поток приглашений, refund после reward, cap/expiry, Free referrer и cancel-scheduled time credit.
- Renewal, cancel, observed provider refund или account close сходятся одновременно без product-side refund workflow.
- Owner теряет роль между render и submit; последний Owner пытается закрыть account, пока workspace содержит Members.
- Пользователь состоит в нескольких workspaces с разными plans; account-level settings не смешиваются с workspace billing.
- Workspace превышает Free limits после downgrade; данные read-only, retention clock, export и deletion описаны до действия.
- Два concurrent storage upgrades; add-on payment unknown; downgrade capacity ниже used bytes; base cancel or separately authorized entitlement correction after observed provider refund при активном add-on; logical delete освобождает quota раньше physical purge.
- Paid workload аномален: fair-use/rate/safety ceiling срабатывает без коммерческого `remaining`, без скрытого overage и без остановки локального capture.
- Renewal unknown at cutoff, поздний success после периода на `Free`, cancel/refusal от payment data одновременно с in-flight operation.
- Локальный desktop offline во время downgrade/cancel; запись уже идёт; upload queue содержит неопубликованные файлы.
- Email receipt/notice не доставлен или verified login email изменён после immutable invoice snapshot.
- Backoffice refund pending/canceled/unknown or original method unavailable remains outside product; GRAF reconciles only authoritative provider/registry truth and never retries a payout.
- Account close требует хранить fiscal/audit records, но meeting/account personal data должно быть удалено в контролируемых GRAF системах.
- Financial pages попадают под PostHog autocapture или Yandex inventory; маскировка/блокировка не настроена.
- Compact/mobile/200% zoom, keyboard-only, screen reader, reduced motion, длинные русские статусы и отключённый JavaScript.
- Один media source разбит на chunks, повторно отправлен или частично успешно обработан на границе Free quota window; overlapping accepted ranges не должны расходовать секунды дважды.

## Requirements *(mandatory)*

### Account, Tenancy And Authority

- **FR-001**: Самостоятельная публичная регистрация MUST через discovery auth context общей SaaS Organization идемпотентно создавать отдельное личное workspace и активную Owner membership; configured login workspace MUST NOT быть production ownership. Multi-organization identity не входит в feature 140.
- **FR-002**: Billing subject MUST быть workspace, а payer/actor MUST быть существующим `UserIdentity`; система MUST NOT вводить параллельную customer/user identity truth.
- **FR-003**: Только active designated billing Owner MUST создавать payment, менять plan/cycle/method/add-on, cancel/resume and apply promo. Published refund/support email remains available after role loss or account close, but external correspondence cannot authorize GRAF workspace access or money mutation. Role loss still vetoes future charges; successor re-consents and binds own method.
- **FR-004**: Admin MUST видеть plan, entitlement и агрегированное usage без payment-method token/mask, receipt contact, tax details, invoices и refund controls; Member MUST видеть только capability и собственное usage.
- **FR-005**: Каждая workspace account/billing mutation MUST повторно проверять session, CSRF, current membership, role и workspace scope в момент исполнения. External refund email is not product input and MUST NOT create a GRAF case, session, authority, entitlement or money mutation.
- **FR-006**: Пользователь с memberships в нескольких workspaces той же auth Organization MUST явно выбирать workspace через POST switch, который rechecks active membership, rotates session/CSRF and tenant context, invalidates stale workspace requests and never mixes billing/entitlement. Cross-organization switch MUST fail closed and is out of scope.

### IA, Navigation And Account Center

- **FR-007**: Кабинет MUST сохранить существующую shared sidebar и добавить account menu без второго navigation shell.
- **FR-008**: User/account menu MUST содержать: `Профиль`, `Безопасность`, `Уведомления`, `Тариф и оплата`, `Пригласить друзей`, `Выйти`; каждый пункт MUST вести в один canonical route и иметь visible focus/current state.
- **FR-009**: Sidebar subscription card MUST показывать реальный server-owned plan/trial/problem state и MUST заменить hardcoded `Пробный период 7 дней`.
- **FR-010**: `Тариф и оплата` MUST быть единым hub с разделами `Обзор`, `Использование`, `Способ оплаты`, `История`, `Скидки`; отдельные конкурирующие меню `Подписка`, `Биллинг` и `Платежи` запрещены.
- **FR-011**: Profile/security/preferences/referral являются account-scoped; plan/usage/payment/history/discount являются workspace-scoped, и UI MUST явно показывать выбранное workspace.
- **FR-012**: Billing/checkout/account-close and the refund instruction MUST быть browser surfaces; the refund request itself is sent through the user’s external mail client to the configured support mailbox. Desktop embedded surface MUST показывать read-only summary, кнопку `Открыть тариф и оплату в браузере`, short-lived one-time authenticated handoff и состояния expired/offline/browser-unavailable/return-to-desktop без передачи финансовых данных в URL.
- **FR-013**: Admin route `/admin/balance` MUST оставаться usage/quota view и быть переименован в UI в `Использование и лимиты`; он MUST NOT притворяться финансовым balance.

### Profile, Security, Preferences And Account Close

- **FR-014**: Пользователь MUST изменять display name, locale, timezone и theme (`Системная`, `Тёмная`, `Светлая`) с preview/save/cancel и одинаковым результатом в web/desktop embedded UI.
- **FR-015**: Security surface MUST показывать linked login methods, sessions и registered devices с last activity, platform и current marker, поддерживать revoke one, revoke all others и sign out all.
- **FR-016**: Unlink login method MUST быть запрещён, если он оставит пользователя без проверенного recovery/login path.
- **FR-017**: Notification preferences MUST разделять обязательные security/financial/receipt notices и optional product/marketing notices; обязательные notices нельзя отключить marketing toggle.
- **FR-018**: Account close MUST иметь versioned 7-day launch cooling policy, exact `finalize_at`, durable states `preview → scheduled_cooling → canceled|finalizing → completed|blocked`, re-auth and cancel-close. Scheduling stops future charges; a Temporal workflow MUST survive timer/restart/retry and recheck cancellation/authority before finalization. Last Owner with other Members is blocked until transfer. For sole-member personal workspace, workflow fans out existing GRAF-controlled meeting deletion, applies FR-019 deletion precedence, waits for terminal/declared external limits, removes workspace non-financial rows/membership, pseudonymizes retained finance, then revokes sessions/devices.
- **FR-019**: Accepted meeting deletion and account-close finalization MUST immediately revoke user access to meeting data, release chargeable playback quota and place `meeting-review.m4a`, current `meeting-transcription.wav`, retained legacy v3/v4 transcription sources and related primary derivatives into the existing mandatory deletion workflow; normal source recovery-retention MUST NOT delay this purge. Only a formally registered mandatory hold with approved authority, bounded reason/scope, creation/review/expiry timestamps and audit MAY defer physical primary purge; if no approved hold capability is enabled, no hold exception exists. Held data remains inaccessible and contributes zero customer quota. Copy MUST NOT обещать universal erasure and MUST distinguish GRAF primary purge, legally retained finance, backup expiry and YooKassa-controlled objects; backups MUST NOT be exposed as user recovery after deletion.

### Plan Catalog, Trial, Entitlements And Usage

- **FR-020**: Versioned plan catalog MUST иметь immutable plan/price/entitlement/offer versions; уже созданный invoice MUST NOT пересчитываться из текущего каталога.
- **FR-021**: Initial public self-service catalog MUST содержать только `Free` и `Личный` с monthly/annual cycle для paid plan; team/enterprise MUST отображаться как отдельный sales-assisted path без self-service charge.
- **FR-022**: Trial MUST начинаться только после explicit Owner action `Начать 7 дней бесплатно`, длиться ровно 7 calendar days from authoritative activation timestamp, не требовать card/offer/recurring consent и не включать автосписание. Право MUST быть unique once per verified `UserIdentity`, независимо от personal workspace, linked login methods, sessions and concurrent requests; registration itself leaves `Free`. До verification основной личности CTA trial MUST быть disabled с причиной `Подтвердите email, чтобы начать 7 дней бесплатно` и действием, открывающим существующий verification flow; скрывать причину или создавать activation запрещено. После authoritative verification eligibility MUST обновляться автоматически без расходования trial. Start/end timestamps and one-time rule MUST быть видимы до подтверждения и после activation. Consequential surfaces show the exact end timestamp and timezone; a relative remainder uses floor days then hours and never rounds up. Expiry projects `Free` without charge.
- **FR-023**: Exact launch prices, limits, provider minimum floor, integer-minor-unit rounding, VAT/receipt mapping and offer version MUST быть утверждены product/finance/legal owners до production enablement и опубликованы как единая server-owned truth для pricing page, checkout, account и receipts; payable total MUST быть положительным и не ниже floor.
- **FR-024**: Usage projection MUST маркировать каждую dimension как `quota` или `unlimited`. Для `Личного` minutes/meetings/transcription/AI MUST показывать `Без лимита` и фактическое использование без invented included/remaining/reset. Для `Free` processing quota MUST быть 300 minutes per fixed calendar window `[day 1 00:00, next month day 1 00:00)` in `Europe/Moscow`, with no rollover and no effect from editable user/workspace timezone; ledger boundaries are converted to UTC once per window. UI показывает included/used/remaining/freshness and exact `reset_at`, rendered in user locale/timezone with the authoritative zone disclosed. Exact usage is rendered as `N мин M сек` (zero-padded seconds), while the 300-minute allowance remains a rounded product label; no meeting is rounded for ledger purposes. Raw token/compute/provider units запрещены.
- **FR-025**: Subscription entitlement MUST проецироваться в существующие workspace quotas/feature decisions и MUST NOT повышать технические safety ceilings.
- **FR-026**: Коммерческий limit MUST применяться к новым server upload/processing/storage/paid AI actions; manual local Record/Stop, visible capture, локальная custody, deletion и разрешённый export MUST NOT блокироваться.
- **FR-027**: Metered usage MUST иметь append-only source-range ledger and reservation/commit/release lifecycle tied to accepted server job/result. Free allowance is exactly `18 000` whole processing seconds per FR-024 window. The reservation stores the selected Moscow-month window; a result crossing midnight commits to that stored window, never to the worker's later current window. Admission reserves declared media duration; commit sums only unique successfully accepted processed ranges, partial success commits only its confirmed range, and failed/canceled/rejected ranges release reservation. A result cannot commit more seconds than its remaining reservation: an overrun is rejected/unaccepted and creates an owned reconciliation gap, never negative remaining or a second charge. Stable source/range uniqueness MUST prevent retry, chunk overlap and concurrent worker double counting. Per-meeting rounding is prohibited. Paid unlimited dimensions record actual accepted seconds for capacity metrics but MUST NOT deny user action from a commercial counter. Daily aggregates MUST reconcile before display.
- **FR-028**: Free processing quota MUST expose a distinct approaching state at 80% (`14 400` committed seconds) and an exhausted state at 100% (`18 000` seconds), each with exact used/remaining/reset copy, affected-action explanation and a recovery CTA (`Начать 7 дней бесплатно`, `Выбрать Личный` or wait for reset as eligible). Storage keeps its separate 80%/95%/100% thresholds. Stale data is an explicit degraded state; color cannot be the only signal. Paid unlimited dimensions MUST NOT показывать approaching/exhausted коммерческий state.
- **FR-107**: Fair-use restriction MUST NOT be a hidden volume quota. It MAY cover proven automated bulk use, resale/service bureau use, technical-limit circumvention or security abuse; normal personal meeting volume, IP, device count or a single statistical anomaly alone MUST NOT be sufficient. A restriction records affected capability, bounded reason class, evidence reference, start and `review_by` no later than 24 hours; shows persistent in-product/email notice, support review and appeal; and preserves local Record/Stop, existing data, export and deletion. Urgent security containment MAY be immediate, while non-urgent restriction requires notice before effect. Technical overload queues/retries or gives a transparent temporary error and never creates an overage charge.

### Storage Quota And Co-termed Add-on

- **FR-093**: Server-owned storage MUST быть workspace-scoped and enforced in decimal bytes. Launch allowances: `Free=250 000 000`, `Trial Личного=500 000 000`, `Личный=2 000 000 000`; one optional add-on selects total capacity `5 000 000 000`, `20 000 000 000`, `100 000 000 000` or `500 000 000 000` bytes. Add-on stacking and self-service capacity above 500 GB are prohibited.
- **FR-094**: Chargeable storage at launch MUST включать только logical bytes активного normalized `meeting-review.m4a` playback artifact in GRAF-controlled primary storage. Database transcript/notes, the current single `meeting-transcription.wav` processing source, legacy v3/v4 `mic.wav`/`incoming.wav` source artifacts, processing derivatives/transient media, replicas/backups, provider temporaries, local files and logically deleted objects MUST NOT считаться. Outside accepted deletion, current and legacy transcription sources remain lifecycle-accounted and purge only after successful transcript import plus verified stored playback under an approved source-retention policy. The retention deadline starts only when both gates are true; policy-version changes recompute the deadline, and losing either verification reopens recovery and cancels the purge deadline. Failures retain recovery truth rather than silently deleting. Accepted meeting deletion/account-close finalization overrides that recovery retention and follows FR-019. User attachment storage is deferred. UI MUST иметь `Что считается хранением?` and MAY show measured hour estimates labeled non-authoritative.
- **FR-095**: Archival storage admission MUST атомарно резервировать declared chargeable normalized playback (`meeting-review.m4a`) bytes; `used + reserved + incoming` MUST NOT превышать capacity. Accepted-before-cutoff archival upload MAY завершиться только в пределах reservation. The verified object stat is authoritative: a smaller object releases the difference, an equal object commits it, and a larger object is rejected/unaccepted with local custody preserved and an owned reconciliation gap. Invalid normalization never commits. Superseding an active playback artifact atomically releases the prior bytes and commits the replacement, so no intermediate double charge is visible. Failed/canceled upload releases its reservation. The transcription WAV and no-archive transient admission MUST NOT consume this reservation. Logical deletion releases user quota immediately, while physical purge remains visible in lifecycle accounting.
- **FR-096**: Storage meter MUST показывать used/reserved/available, exact capacity, freshness and threshold states at 80%, 95% and 100%. At 100% new archival uploads are blocked; existing data remains readable/exportable/deletable, local Record/Stop and local custody remain available, no-archive processing follows FR-106, and no data is auto-deleted.
- **FR-097**: Storage add-on MUST быть co-termed with base `Личный`, share its cycle/renewal anchor and appear as a separate invoice/receipt line. Initial checkout charges full base+add-on. During a paid interval, mid-cycle upgrade amount in minor units is `floor((target_period_price - current_period_price) × remaining_billable_seconds / full_billable_interval_seconds)` using UTC boundaries and excluding any zero-money referral interval; confirmed capacity remains active through a subsequent bonus interval. During an already active bonus interval, upgrade is scheduled for the next paid renewal and current capacity stays unchanged. If positive result is below provider floor, UI schedules the upgrade at renewal instead of rounding up or making a zero payment. Downgrade/removal takes effect at next paid renewal with no hidden credit/refund.
- **FR-098**: Exactly one active or scheduled storage capacity selection MUST exist per workspace. Concurrent base/add-on checkout, capacity changes, cancel, renewal, time credit and account close MUST serialize on workspace subscription; price/capacity/version snapshots are immutable.
- **FR-099**: Trial/Free cannot buy a standalone add-on. Trial expiry, base cancel/failure or a separately authorized entitlement-ending correction after observed refund projects the target Free/base capacity at the same cutoff. If actual storage exceeds new capacity, data stays read-only/exportable/deletable under existing retention and new uploads remain blocked until usage is reduced or paid capacity is restored.
- **FR-100**: Add-on price/cycle/pro-rata rounding, normalized playback format/bitrate, transcription-WAV retention deadline, exact object-size writer and full storage COGS/backup multiplier MUST pass explicit product, unit-economics, finance, accounting, legal, storage and privacy validation before production enablement. Current 64 kbit/s playback and 256 kbit/s transcription hour equivalents are estimates only; no approximate hours claim may replace byte truth without a versioned measured conversion.
- **FR-106**: When archive capacity is full, GRAF MUST offer `Обработать без сохранения аудио` on `Free`, Trial and `Личный` for every otherwise accepted new recording or manual media upload within the same published technical format/size/security limits and explicitly selected as no-archive; there is no additional commercial eligibility rule. Free reserves/commits exact seconds under FR-027 and denies only when its processing quota is exhausted; Trial/`Личный` have no commercial processing counter. An archival/playback request remains storage-bound. Transient media is excluded from chargeable storage, cannot be replayed after processing, MUST purge within 15 minutes after terminal success/failure, and MUST be force-purged/cancel the job no later than 24 hours after admission even after worker crash/stuck processing; only transcript/notes and their DB metadata remain. If transient admission is unavailable, UI states that processing has not started and keeps local custody. This path cannot silently replace an archival upload selected by the user.

### Checkout, Payments And Provider Truth

- **FR-029**: Launch checkout MUST использовать hosted YooKassa redirect и MUST NOT собирать, передавать через GRAF UI, хранить или логировать PAN/CVC.
- **FR-030**: Checkout summary MUST показывать plan/cycle, unlimited scope/technical limits, base and optional storage add-on lines/capacity, amount today, applied discount, normal next amount/date, auto-renewal, immediate-Free failure, cancel/data consequences, static email-only external refund boundary and versioned offer acceptance before payment.
- **FR-031**: Checkout MUST иметь отдельные unchecked controls `Принимаю оферту версии …` и `Соглашаюсь на автопродление и рекуррентные платежи` со ссылками, field error and re-consent при смене версии. GRAF MUST сохранять evidence с actor/workspace/version/timestamp; сбор IP/UA допускается только если approved retention policy требует это.
- **FR-032**: Client/return URL/webhook body MUST NOT активировать entitlement; provider object, прочитанный server-to-server и проверенный по shop/test/amount/currency/metadata, является authority.
- **FR-033**: Одна logical billing operation MUST сохранять internal operation key без срока истечения; каждый provider mutation MUST использовать сохранённый idempotence key/request snapshot and `provider_key_expires_at`. До 24h unresolved retry reuses same body/key; после expiry automatic mutation retry MUST stop, а object absence MUST подтверждаться GET/list/reconciliation before an owned manual resolution or explicit new user operation.
- **FR-034**: Internal uniqueness and locking MUST предотвращать duplicate invoice, concurrent active charge attempt и повторное применение event даже после provider 24-hour idempotency window.
- **FR-035**: Provider webhook MUST allowlist `payment.succeeded`, `payment.canceled`, optional two-stage `payment.waiting_for_capture`, observed `refund.succeeded`, `payment_method.active`; deduplicate в durable inbox, проверять current published source network/trusted-proxy/TLS configuration и authoritative GET, применять monotonic event version/transition и отвечать без cross-tenant disclosure. Non-success method states MUST завершаться polling/reconciliation; GRAF has no pending refund lifecycle.
- **FR-036**: Payment attempt MUST хранить confirmed provider id/status/cancellation reason class без raw webhook body, card data или unsafe metadata.
- **FR-037**: Payment method reference MUST быть opaque, encrypted at rest with versioned key id/dual-read rotation, masked in UI/logs, доступен только billing service и deny-by-default после cancel/revoke/permission_revoked.
- **FR-038**: Изменение method MUST завершаться только после zero-amount hosted binding, `payment_method.active`/authoritative verification and real-shop capability gate; старый active method не отключается до подтверждения нового. Если binding capability недоступна, self-service replacement MUST быть disabled без small-payment/refund fallback.
- **FR-039**: Payment state vocabulary MUST различать `checkout_pending`, `processing`, `succeeded`, `canceled`, `unknown`, `method_required`; UI MUST показывать безопасный следующий шаг для каждого состояния.

### Subscription Lifecycle And Renewal Resolution

- **FR-040**: Commercial subscription MUST иметь состояния `trialing`, `free`, `active`, `cancel_at_period_end`; renewal operation отдельно имеет `scheduled`, `sent`, `unknown`, `succeeded`, `canceled`, `manual_resolution`. `past_due`, `grace`, `suspended` и paid-access grace запрещены. Каждый transition audited; stale events rejected by monotonic application version.
- **FR-041**: Renewal schedule, amount, cancel_at_period_end и stop-future-charge truth MUST принадлежать GRAF, а не выводиться из последнего YooKassa payment.
- **FR-042**: Renewal launch MUST создавать ровно одну automatic charge operation per period. Confirmed failure MUST NOT schedule T+ retries; at exact `paid_through` workspace becomes `Free`, auto-renewal becomes off and manual resume requires fresh summary/consent.
- **FR-043**: Outcome classifier MUST различать confirmed success, final canceled/action-required and transport `unknown`. Same-key GET/transport recovery of one unknown operation is not a new charge; silent new-key retries are prohibited.
- **FR-044**: HTTP 500/timeout with unknown outcome MUST до provider key expiry повторять exact operation/key or GET. After expiry, fail closed into owned gap and never create a new payment/binding until absence/manual closure is proven. Each GRAF-originated provider operation snapshots current recurring-authority version and MUST recheck it under the same workspace lock immediately before network mutation; GRAF never originates refund execution.
- **FR-045**: Cancel renewal MUST быть self-service, называться `Отключить автопродление`, показывать end date/consequences, не требовать причины and electronically record refusal from future use of saved payment data. It immediately vetoes future jobs. Refusal timestamp before provider mutation wins; an already in-flight unknown is resolved without new charge, and late success creates an internal financial incident plus support-email notice, not a product refund case.
- **FR-046**: Retention/save offers (`более дешёвый тариф`, `пауза`) MAY быть показаны как optional alternatives, но MUST NOT скрывать, переименовывать или блокировать cancel action.
- **FR-047**: Resume MUST требовать usable payment method, показывать next amount/date и не списывать деньги немедленно без отдельного preview/consent.
- **FR-048**: At `paid_through`, cancel/final failure/unconfirmed unknown MUST immediately project `Free`; unknown exposes `renewal_resolution_pending` and blocks manual pay. Accepted-before-cutoff jobs finish; unaccepted queue stays local. Late success restores a full term only when no effective refusal/cancel/withdrawal/account-close precedence exists; otherwise recurring authority stays off and FR-104 applies. Downgrade never starts deletion.

### Invoices, Receipts And Observed Refund Reconciliation

- **FR-049**: Mutable/versioned Checkout Intent MUST own preview and bounded promo reservation. Before provider mutation an intent may expire without invoice. Invoice becomes immutable immediately before mutation; once payment is `pending|unknown`, invoice/promo MUST remain locked and block replacement even after UI timeout. Only authoritative final `canceled` (including confirmed expiration cancellation reason) may void/release/supersede; late hosted success MUST resolve to the original invoice without a second payable invoice.
- **FR-050**: Payment receipt items total MUST точно совпадать с payment amount. GRAF MUST NOT construct or send refund execution/receipt payloads. Refund receipt creation is a YooKassa backoffice responsibility; GRAF only reconciles authoritative observed refund/receipt outcome. Скидка отражается итоговой ценой positive service line.
- **FR-051**: Personal-launch receipt contact MUST быть masked verified primary login email and restricted immutable snapshot per invoice/payment. Launch payment mode is `full_payment` only after finance/legal approval; `full_prepayment` or any mode requiring a separate settlement receipt MUST block launch pending a separate lifecycle slice. UI distinguishes registration from email delivery: `canceled` alerts/escalates immediately; only `pending` is polled and escalated at 3 days.
- **FR-052**: Payment history MUST показывать invoice number, period, amount, payment status, discount, masked method, receipt availability and a static refund/support email instruction without provider token/raw id, refund result, case, form, status or timeline.
- **FR-053**: Cabinet MUST показывать configured refund/support address, safe invoice reference, `Написать письмо` and warnings not to send card data, provider ids or meeting content. GRAF MUST NOT receive/store the request as a product entity, promise a product SLA, verify/triage/decide it, calculate an amount, expose case status or call a refund API. Support correspondence and mandatory legal deadlines are governed by the external merchant backoffice process.
- **FR-054**: Refund eligibility, calculation, approval, communication and execution MUST remain outside GRAF in the approved support/backoffice process and YooKassa merchant cabinet. No refund case, execution command, amount field, evidence upload, operator screen or refund-notification workflow may be added by feature 140.
- **FR-055**: GRAF MUST ingest only authoritative observed provider refund/receipt truth through allowlisted provider read/webhook/registry reconciliation, idempotently bind it to the original confirmed payment and never originate, retry or duplicate a payout.
- **FR-056**: Observed refund reconciliation and any separately authorized entitlement/referral correction MUST have immutable metadata-only audit with actor/source/provider-reference class/outcome/reason and before/after; support email content and backoffice decision evidence MUST NOT enter product logs, analytics or broad audit. Any four-eyes action threshold is a versioned launch-gate value in minor units; approver and executor MUST be distinct named roles for provider and off-provider corrections, and an unset threshold or role mapping blocks enablement.
- **FR-102**: A provider refund observation MUST NOT automatically restore recurring authority or infer claim basis. Any entitlement/add-on correction requires a separate explicit audited backoffice decision; referral maturity/reversal MAY use authoritative confirmed refund amount/timestamp under FR-064/FR-069. No refund state is rendered to the user.
- **FR-103**: Recurring payment authority MUST be first-class append-only evidence (`accepted|refused`, purpose/version, actor/source, `recorded_at`, `effective_at`) plus current monotonic authority version/allowed flag. `Отключить автопродление`, separate self-service payment-data refusal and account-close scheduling use the same atomic service; free-form refund email MUST NOT mutate this authority. A mutation authorized under version N MUST fail before network call if current version changed; database commit order is authoritative for equal timestamps, and an already-started outbound call is classified as a late result under FR-104 rather than silently winning. UI and email persist a refusal confirmation with exact time.
- **FR-104**: Late-success precedence MUST be deterministic: without effective refusal it creates an append-only full-duration entitlement grant from `access_restored_at`; with earlier cancel/payment-data refusal/account close it never restores recurring authority or access by default, keeps workspace `Free`, creates an internal financial incident and sends a support-email notice. Backoffice resolves refund or correction outside the product; no refund case or user-facing choice workflow is created in GRAF.
- **FR-105**: Invoice MUST immutably store purchased duration and planned interval; confirmed payment creates a separate append-only actual Entitlement Grant. Normal success uses planned interval; late success uses actual restoration interval. History/notices show both only when they differ. Fiscal service line MUST identify plan/cycle/duration without promising a final calendar interval that can shift before authoritative success.

### Promotions

- **FR-057**: Promo lifecycle MUST включать normalized code, eligibility, validity timezone/window, plan/cycle scope, first/new/existing customer rule, global/per-user caps, discount and redemption snapshot; final payable amount below approved provider floor MUST be ineligible for launch.
- **FR-058**: Code comparison MUST быть case-insensitive по канонической нормализации и MUST защищаться от whitespace/Unicode/confusable ambiguity; raw code не попадает в analytics/logs/evidence.
- **FR-059**: Preview MUST NOT резервировать скидку бесконечно; invoice creation atomically revalidates/reserves/redeems. Pre-provider abandoned intent may release by expiry; after provider mutation reservation releases only after authoritative final `payment.canceled`, never from UI timeout/unknown state.
- **FR-060**: Один invoice MUST применять не более одной price discount; при promo и referral intro-discount выбирается наиболее выгодная допустимая и UI объясняет выбор.
- **FR-061**: Promo error copy MUST различать `недействителен`, `истёк`, `не подходит`, `уже использован` только там, где это не раскрывает abuse-sensitive campaign capacity.

### Referral Program

- **FR-062**: Referral program MUST использовать один opaque link (без отдельного вводимого кода), first-touch attribution, referrer/referee identity, campaign version, status and expiry; attribution после регистрации не перезаписывается другой ссылкой.
- **FR-063**: Referee reward launch version MUST be 10% off the first eligible paid period; referrer reward MUST be non-cash service time credit: 7 calendar days for first monthly payment or 30 calendar days for first annual payment after maturity.
- **FR-064**: Referrer reward MUST пройти `attributed → registered → paid → pending_maturity → available`; authoritative provider-confirmed refund or abuse decision MUST создавать `reversed/rejected`, а не удалять history.
- **FR-065**: Time-credit ledger MUST быть append-only, workspace-bound and unique by referee first-payment source. Entry stores `days`, grant/expiry, target workspace, applied interval and reversal-of. Mutable balance/wallet and cash value are prohibited.
- **FR-066**: Self-referral, existing-account reuse, duplicate attribution and duplicate reward MUST быть blocked; device/payment/domain/IP совпадения являются risk signals, а не единственным окончательным доказательством.
- **FR-067**: Campaign MUST иметь velocity, 180 granted-day cap per target workspace in rolling 12 months, global caps, 14-calendar-day maturity, pause while a security review is open, 12-month unapplied expiry for `Free`, manual review threshold and appeal path. An authoritative provider-confirmed refund before maturity prevents availability; a later confirmed refund follows FR-069. One referee yields one 7/30-day reward based only on first paid cycle.
- **FR-068**: Referrer UI MUST показывать aggregate/history status и masked identity только в объёме, необходимом для понимания приглашения; полный email/referee profile запрещён. Если у account есть несколько personal workspaces, UI MUST явно выбрать и показать target workspace для workspace-bound time credit (по умолчанию текущий personal workspace), а выбор не должен менять entitlement или платежные данные.
- **FR-069**: Authoritative provider-confirmed refund or charge abuse decision MUST создавать bounded reversal: unapplied future credit is removed by append-only entry; already consumed calendar days never create negative time, cash debt or shortening of a separately paid period. Cancel-scheduled still receives earned credit before final Free transition.
- **FR-101**: Available time credit MUST применяться как contiguous zero-money interval after confirmed paid period. Для active renewal он сдвигает charge anchor; для cancel-scheduled — только final service/add-on cutoff согласно FR-108. Because storage add-on is co-termed, the currently active capacity remains through the bonus interval. For `Free`, credit remains unapplied until first own paid success or 12-month expiry. Credit never creates YooKassa payment/receipt; UI shows paid-until, bonus-until and next charge separately.
- **FR-108**: For `cancel_at_period_end`, a matured referral credit MUST extend only the final non-renewing service/add-on cutoff and MUST NOT create a future renewal job or `next charge`. Multiple credits append contiguously. UI shows `Следующее списание: не запланировано`; resuming renewal before final cutoff uses the resulting shifted anchor.

### Notifications And CX

- **FR-070**: Transactional notification outbox MUST быть idempotent и покрывать trial end (T-3 days, T-24h), renewal reminder (T-3 days), payment success, confirmed failure→Free, unknown/late resolution including charged-after-refusal, recurring-authority refusal, cancel/resume, method required, storage 80/95/100%, transient purge incident, fair-use review/appeal, add-on change, receipt and referral time credit; no refund-case transition or retry/grace notice exists.
- **FR-071**: Financial notice MUST содержать human-readable event, exact relevant date/amount where authorized and one safe next action. Browser-managed events use a safe deep link; any support/refund correspondence remains outside the product outbox. Raw provider ids, tokens, email of referee and meeting content запрещены.
- **FR-072**: Mandatory financial/security/receipt notices MUST доставляться независимо от marketing preference и иметь documented delivery/retry/failure state.
- **FR-073**: Каждая error/empty/loading/success state MUST объяснять, сохранились ли деньги, entitlement и pending operation, и предлагать один safe next action.
- **FR-074**: Support surface MUST позволять скопировать safe billing reference и открыть `Написать письмо` to the configured refund/support address without transferring secrets, card data, provider ids, raw provider payload or meeting content; no public refund request/case/status/SLA/amount/result state exists. If a mail client is unavailable, keyboard-accessible copy actions remain available.

### Security, Privacy, Analytics And Compliance

- **FR-075**: YooKassa shop id/secret и API calls MUST быть server-side; test/prod credentials, shops, webhooks, databases/flags MUST быть разделены.
- **FR-076**: Financial pages MUST иметь explicit analytics page class and masking: Yandex/replay запрещены; PostHog MUST NOT capture amount, promo code/referral-link token, provider/invoice/payment/refund ids, receipt contact, tax/payment method data or form values.
- **FR-077**: Logs, diagnostics, screenshots and committed evidence MUST быть metadata-only and MUST NOT содержать secrets, raw webhook/provider payload, card data, receipt contact, real account/payment identifiers or private meeting content.
- **FR-078**: Каждая billing/promo/referral tenant table MUST иметь declared RLS isolation, runtime inventory, same/cross-tenant tests and fail-closed policy before merge.
- **FR-079**: Sensitive financial/admin actions MUST иметь immutable metadata-only audit с actor/workspace/action/target class/outcome/reason/source and timestamp.
- **FR-080**: Legal/finance launch gate MUST подтвердить organisation/ИП, YooKassa contract/recurring/binding, 54-ФЗ scenario, VAT/payment subject/mode, offer/auto-renew/immediate-Free/add-on/static refund-email boundary/time-credit/unlimited-fair-use copy, electronic refusal from saved payment data, financial retention and account-deletion wording.
- **FR-109**: Emergency stop MUST block every GRAF-originated provider money mutation, while preserving the external support/refund backoffice, self-service refusal from future charges, cancellation, history, support reference, local Record/Stop, deletion and export. GRAF has no refund execution to block.

### Accessibility, Responsive UI And Brand Distance

- **FR-081**: Account and billing surfaces MUST быть Russian-first, localizable, original GRAF dark/light design and pass clean-room brand-distance review; Krisp/competitor assets/copy/trade dress запрещены.
- **FR-082**: Account/billing GRAF surfaces MUST целиться в WCAG 2.2 AA: все действия keyboard-operable, focus видим и не obscured, help находится consistent, labels/instructions/errors/live status/read order корректны, selected/focus различимы, verified data не вводится повторно и re-auth имеет accessible alternative. Hosted YooKassa является внешней conformance boundary; GRAF MUST дать доступный fallback/support path при provider accessibility blocker.
- **FR-083**: Minimum interactive target MUST быть не меньше 24×24 CSS px с достаточным spacing; critical confirmation buttons SHOULD быть не меньше 40px по высоте.
- **FR-084**: Forms MUST иметь field-level errors и summary, не полагаться только на color, сохранять безопасный input после recoverable failure и не просить повторную оплату при unknown state.
- **FR-085**: Layout MUST работать при compact desktop, mobile browser, 200% zoom/reflow, long Russian strings, reduced motion and disabled JavaScript fallback for critical navigation/status.
- **FR-086**: Checkout/cancel/account-close confirmation MUST использовать explicit action labels (`Оплатить … ₽`, `Отключить автопродление`, `Закрыть аккаунт`) вместо `Продолжить`/`Да`; refund instruction uses `Написать письмо` and MUST NOT imitate an in-product submission confirmation.

### Operations, Reconciliation And Public Launch

- **FR-087**: Billing operations MUST иметь webhook fast path, polling stuck payments/observed refunds/receipts/methods, periodic provider API reconciliation and audited manual daily YooKassa CSV import. Payments and refunds are separate required report kinds; each import MUST bind shop/environment/schema/language/config version, Moscow report date, part/last-part, row identity and content hash, prove completeness including configured empty reports, handle safe replacement/missing/malformed files, restrict retention and record gap owner. SFTP automation is out of scope.
- **FR-088**: Emergency `stop all charges` MUST блокировать новые GRAF checkout/renewal/binding, сохраняя read-only history, external support/refund backoffice, electronic payment-data refusal, self-service cancel and product availability outside money mutation.
- **FR-089**: Monitoring MUST покрывать payment success/cancellation reasons, unknown age, webhook lag/errors, immediate-Free projection, duplicate prevention, storage used/reserved/reconciliation, add-on/time-credit jobs, observed provider-refund/receipt reconciliation gaps and notification failures without private payloads; no refund-case age/SLA metric exists in GRAF.
- **FR-090**: Test shop E2E MUST покрывать bank-card initial success/saved true/false, zero binding, recurring/declines, UI-expired hosted payment that later succeeds, 23:59/24:01 idempotency boundaries for payment/binding, duplicate/out-of-order webhook, provider floor, manual merchant-cabinet full/partial refund observation, refund receipt reconciliation, immediate receipt-canceled alert, pending 3-day escalation and complete separate payments/refunds registry sets; GRAF MUST issue zero refund API calls.
- **FR-091**: Production enablement MUST пройти controlled real-shop canary: small base+add-on payment, webhook+GET, unlimited/storage entitlement, receipt, manual merchant-cabinet refund outside GRAF, observed refund receipt and registry reconciliation with zero product refund cases/execution calls.
- **FR-092**: Public rollout claim MUST оставаться bounded until separate product/security/legal/finance/QA/release approvals and current global `pilot_blocked` gaps are closed; payment smoke alone не означает production ready.

### Key Entities

- **Personal Workspace Provisioning**: Идемпотентное создание самостоятельного workspace и Owner membership при публичной регистрации.
- **Plan And Price Version**: Неизменяемая версия названия, cycle, цены, валюты, налогово-чековой конфигурации, entitlements, offer и effective window.
- **Workspace Subscription**: Workspace-scoped trial/free/paid lifecycle, billing anchor, current period, cycle, cancel, unknown-resolution projection and default payment method truth.
- **Trial Activation**: Append-only atomic once-per-verified-`UserIdentity` activation evidence with target personal workspace, policy version and authoritative start/end timestamps; workspace creation alone does not consume it.
- **Entitlement Snapshot**: Версия capabilities с dimension mode `unlimited|quota`, storage capacity и action decision.
- **Free Usage Window**: Unique workspace/capability/policy window with fixed `Europe/Moscow` boundaries, UTC start/end projection, `18 000`-second allowance, no rollover and exact source-range reservation/commit/release reconciliation.
- **Storage Capacity Add-on**: Co-termed versioned target capacity, price/cycle/pro-rata snapshot, active/scheduled transition and base-subscription dependency.
- **Storage Reservation / Inventory Entry**: Exact logical byte admission, commit/release/delete source and reconciled projection.
- **Invoice**: Неизменяемый расчёт одного периода с price/tax/discount/referral snapshots и amount due.
- **Payment Attempt**: Одна попытка оплаты invoice с logical operation key, provider idempotence, confirmed state and bounded cancellation class.
- **Saved Payment Method**: Зашифрованная opaque provider reference и маскированная presentation без card credentials.
- **Webhook Inbox Event**: Дедуплицированный bounded signal для authoritative provider read; raw payload не хранится как audit evidence.
- **Observed Provider Refund**: Internal reconciliation-only projection bound to the original payment with authoritative provider status/amount/timestamp and audit; it has no support-request content, product case lifecycle, operator controls or user-facing representation.
- **Receipt State**: Регистрация электронного чека прихода/возврата, polling/escalation и отдельно лишь observed delivery truth без ложного provider-confirmed email delivery.
- **Promotion Campaign / Redemption**: Versioned eligibility/discount/caps и атомарный snapshot применения.
- **Referral Campaign / Attribution**: First-touch relationship и lifecycle приглашённого.
- **Time Credit Ledger Entry**: Append-only 7/30-day service credit, target workspace, application interval, expiry or reversal without cash value.
- **Transactional Notice**: Idempotent финансовое/security сообщение с delivery state.
- **Billing Audit Event**: Metadata-only финансовый audit, который может безопасно проецироваться в существующий admin journal.
- **Reconciliation Gap**: Несовпадение internal/provider/registry truth с owner, severity, resolution and timestamps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% самостоятельных production-like registrations создают отдельное personal workspace; cross-tenant тесты находят 0 доступов к чужим account/billing данным.
- **SC-002**: В moderated usability проверке не менее 90% новых пользователей за 2 минуты находят тариф, paid `Без лимита`, storage used/available/add-on, дату/сумму следующего списания, cancel, `Обработать без сохранения аудио`, referral target workspace и email-only refund instruction с safe invoice reference.
- **SC-003**: Test-shop matrix и production canary создают ровно один invoice и одно подтверждённое entitlement transition для double-click, duplicate/out-of-order webhook, return reload and concurrent worker scenarios.
- **SC-004**: 100% paid entitlement activations основаны на authoritative provider read; redirect/webhook-body-only activations равны нулю.
- **SC-005**: Cancel path завершается self-service не более чем за 3 экрана и 60 секунд; reason optional, future charge job count после подтверждения равен нулю.
- **SC-006**: Usage/storage reconciliation совпадает с source-backed records на 100%; paid unlimited dimensions никогда не получают commercial-limit denial, а storage concurrent admission никогда не превышает capacity кроме explicitly reserved accepted bytes.
- **SC-007**: 100% promo/referral concurrency/fraud fixtures не создают duplicate redemption/reward; first monthly/annual source создаёт ровно одну 7/30-day entry, rolling cap не превышает 180 days.
- **SC-008**: 100% payment/observed-refund/receipt objects past the configured reconciliation threshold либо reconciled, либо представлены открытым gap с owner; silent stale financial states равны нулю and refund-case/SLA objects in GRAF equal zero.
- **SC-009**: Privacy scan на account/billing templates, events, logs and evidence находит 0 secrets, PAN/CVC, raw provider payloads, receipt contacts, raw codes and real account/payment identifiers.
- **SC-010**: Keyboard/screen-reader/zoom matrix покрывает 100% critical account, checkout, cancel, payment recovery, refund email instruction/action and account-close surfaces без keyboard trap и недоступной primary action.
- **SC-011**: Transactional notice deduplication отправляет не более одного сообщения на logical event/channel; failure notice содержит exact Free cutoff/no-retry/manual action, unknown notice не предлагает pay-again, storage notice содержит exact used/capacity/recovery.
- **SC-012**: Production enablement остаётся заблокированным, пока не закрыты 100% legal/finance/security/QA/provider/reconciliation launch gates и current product rollout blockers. Каждый gate имеет named owner, evidence class/reference, approved-at, valid-until/revalidation, revocation state и бинарный blocking outcome; отсутствие свежего evidence считается fail.
- **SC-013**: Unverified identity sees one verification action and creates zero trial activations; after authoritative verification eligibility updates without a new signup. Concurrent requests, multiple personal workspaces and linked login methods for one verified `UserIdentity` create exactly one trial activation; signup without explicit confirmation creates zero activations and trial expiry creates zero charge attempts.
- **SC-014**: Month-boundary concurrency at `00:00 Europe/Moscow` creates exactly one new Free usage window; 100% accepted usage entries belong to exactly one window, prior unused minutes never appear in the new allowance and timezone preference changes do not alter boundaries.
- **SC-015**: For every Free fixture, committed usage equals the deduplicated sum of accepted whole source-range seconds exactly; failed/canceled/rejected ranges contribute zero, partial success contributes only its accepted range and splitting/retrying media changes the result by zero seconds.
- **SC-016**: At full archive capacity, the same no-archive processing flow is reachable on `Free`, Trial and `Личный`; Free commits the exact accepted seconds once, Trial/`Личный` commit no commercial balance, and 100% paths create no persistent playback media.
- **SC-017**: Storage admission enforces exact decimal capacities 250 MB/500 MB/2 GB/5–500 GB against normalized playback bytes only; `meeting-transcription.wav` bytes affect internal COGS/lifecycle but change customer used/remaining by exactly zero, and every estimated-hour label is identified as non-authoritative.
- **SC-018**: In 100% meeting-deletion and account-close-finalization fixtures, read/download access and chargeable playback quota disappear at accepted deletion, every current/legacy primary audio artifact enters the mandatory deletion workflow without normal recovery-retention delay, and zero artifacts remain in a recoverable state unless an active formally valid mandatory hold is present; backup-expiry truth remains separately disclosed.

## Assumptions

- GRAF запускается Russia-first, рублёвый self-service payment идёт через один YooKassa shop.
- Existing passwordless/federated auth, Workspace/UserIdentity/Membership, RLS, admin usage models, Jinja/HTMX cabinet, Postgres, Postal and Temporal are retained.
- Первичная коммерческая модель: `Free` + один paid `Личный`, explicit once-per-identity 7-day cardless trial, monthly/annual cycle, unlimited paid meetings/transcription/AI and separate playback archive capacity. Recommended versioned hypothesis: Free 300 minutes/month + 250 MB, Trial 500 MB, `Личный` 790 ₽/month or 7 900 ₽/year + 2 GB, total-capacity add-ons 5/20/100/500 GB. Add-on price schedule and transcription-WAV retention deadline remain explicit approval gates; checkout stays off until resolved.
- `WorkspaceUsageDaily`/`UserUsageDaily` становятся trustworthy только после source-backed writer, freshness и reconciliation. Storage needs exact object-size inventory/reservations; display-only daily rows не являются quota truth.
- Hosted YooKassa checkout и zero-amount binding используются только после real-shop enablement; если binding недоступен, fallback требует отдельного approved UX без raw card collection.
- Financial operator handles refund email/decision/execution entirely outside GRAF in the approved support process and YooKassa merchant cabinet; GRAF has only read/reconcile tooling for authoritative provider refund/receipt observation and no refund/correction UI or execution CLI.
- Referral maturity и campaign values versioned; default design intent — reward only after paid use and refund window, not immediately after signup.

## Dependencies

- Активный YooKassa merchant agreement, production shop, recurring payments, hosted payment scenario and approved binding capability.
- Approved public offer, privacy/cookie terms, recurring consent, refund policy, 54-ФЗ receipt scenario, tax/VAT mapping and financial retention.
- Existing auth/session/device, tenant context/RLS, workspace roles, admin quota/usage models, cabinet shell, Postal delivery and Temporal worker runtime.
- Product/finance unit-economics approval for base/add-on price, canonical media size/retention/backup multiplier, Free allowances and unlimited fair-use wording.
- Russian legal/finance approval for electronic payment-data refusal, static refund-email wording and the external merchant backoffice refund policy/runbook; eligibility, calculation, approval and mandatory response deadlines remain outside product feature 140.
- Separate closure of global GRAF public rollout blockers; feature 140 cannot override `pilot_blocked` by itself.

## Out Of Scope

- Multiple payment providers, App Store/Google Play billing, international currencies/taxes and cross-border merchant-of-record.
- Team/seat self-service pricing, seat proration, mixed plans inside one workspace, enterprise invoices and sales contracts.
- Usage overage, auto-top-up, paid AI credit packs, outcome billing or dynamic pricing; standalone/stacked storage packs and self-service storage above 500 GB.
- Cash referral payouts, affiliate commissions, bank/KYC/payout rails and withdrawable wallet.
- One-off lifetime deals, gift cards, peer-to-peer transfer of rewards.
- Chargeback/dispute automation beyond recording authoritative provider state; merchant handling remains outside GRAF.
- Full internal financial superadmin/backoffice UI; refund email and merchant workflow remain outside GRAF, and the product has no refund backoffice/workflow.
- Redesign of meeting review/capture or replacement of the existing GRAF design system.
- Claiming full public launch readiness before all other product rollout blockers are independently closed.
