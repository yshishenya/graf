# Feature Specification: Надёжный и безопасный обмен встречами

**Feature Branch**: `125-meeting-sharing`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Новая фича: разобраться, почему не работает кнопка «Поделиться», продумать бизнес-, системную и техническую логику модалки, изучить Krisp, Read.ai и похожие продукты, сделать безопасную вирусную механику и поиск контактов через календарь и адресную книгу."

## Problem Statement

Сейчас пользователь может увидеть рабочее на вид приглашение по email, хотя
внешняя доставка отключена политикой окружения. После отправки сервер отвергает
запрос, а интерфейс показывает общий текст ошибки без объяснения и следующего
действия. Поиск известных людей также слишком узок: он ищет только отображаемое
имя внутри workspace и не использует уже доступный календарный контекст.

Фича должна сделать Share честной точкой управления доступом, а не просто
формой отправки email. Получатель должен быстро понять ценность GRAF, получить
ровно разрешённый объём встречи и иметь прозрачный путь попробовать GRAF самому.

## Scope And Non-Goals

Входит:

- исправление рассинхронизации между доступными серверными capability и
  элементами модалки;
- новый первый экран Share с понятным scope, состояниями приглашения и списком
  доступа;
- безопасное приглашение известных workspace-пользователей и, при включённой
  политике доставки, внешних адресов;
- предложения из участников связанного события календаря и разрешённого
  workspace directory;
- проектирование адресной книги через явный пользовательский picker с
  минимальным доступом;
- получательский summary-first экран, onboarding и измеримая referral-атрибуция;
- revoke, expiry, rotation, audit, rate limits, feature flags и rollback.

### Безопасная очередность поставки

Фича поставляется по независимым воротам. В эту реализацию входят два
контролируемых пути: B2B authenticated summary-only доступ для active workspace
identity и B2C exact-email приглашение внешнему получателю через единый вход с
полным пакетом записи.
При открытии invitation magic link аккаунт создаётся автоматически внутри этого
явного действия; отдельный registration flow не требуется. Получатель не вводит
пароль или код: одноразовая ссылка из приглашения подтверждает приглашённый
email и открывает страницу записи. На ней доступны саммари, расшифровка с
таймкодами, прослушивание, скачивание канонического аудио и экспорт
«расшифровка + саммари»; готовность и политика egress остаются серверным
источником истины. После создания аккаунта GRAF отправляет отдельное
подтверждающее письмо со ссылками на кабинет и настройки. B2C остаётся
operator-gated и выключен по умолчанию; включение
возможно только при настроенных Temporal, email, encryption key, public base
URL, rate-limit, delivery и deletion checks. Public links, native address-book
picker и referral attribution остаются отдельными gated extensions.

Participant distribution, owner auto-share, recurring pre-read, team access и
channel/calendar distribution также описаны как последующие extensions. Они не
включаются автоматически вместе с B2C email: массовое распространение требует
собственной idempotent operation/run authority.

Не входит в первую поставку:

- автоматическая отправка встречи всем участникам календаря без выбора владельца;
- автоматическое добавление получателя в workspace;
- публичный доступ или anonymous full-meeting просмотр по умолчанию;
- бессрочные ссылки, массовый импорт адресной книги, скрытый сбор контактов,
  реферальные выплаты и gamification;
- изменение capture, transcript, playback, export или deletion authority.

В B2C первой поставки получатель получает `full_meeting/view-only` доступ на
bounded срок без membership в workspace. Письмо и экран до входа содержат
только безопасные metadata встречи и ссылку на единый вход; transcript, audio
и summary text появляются только после проверки exact verified identity на
странице записи. Получатель не получает календарные, служебные или внутренние
revision-данные встречи.

## Clarifications

### Session 2026-07-26

- Q: Нужно ли открывать разрешённую запись сразу после открытия одноразовой
  ссылки? → A: Да. Открытие ссылки считается явным действием получателя. GET
  остаётся без побочных эффектов: он только создаёт server-side continuation,
  после чего браузер автоматически отправляет существующий CSRF-bound POST. При
  отключённом JavaScript остаётся одна видимая кнопка-фолбэк.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Поделиться без мёртвого действия (Priority: P1)

Владелец встречи открывает Share и сразу понимает, с кем и чем можно
поделиться в текущей политике. Интерфейс показывает только реально доступные
действия и не открывает модалку сам по себе.

**Why this priority**: Неработающая кнопка разрушает доверие к продукту и
мешает основному сценарию распространения ценности GRAF.

**Independent Test**: В синтетическом workspace с выключенной внешней доставкой
открыть Share, проверить доступное состояние, выбрать известного внутреннего
пользователя и убедиться, что приглашение/доступ создаются. Повторить для
выключенной политики и убедиться, что сетевой запрос недоступного действия не
выполняется.

**Acceptance Scenarios**:

1. **Given** встреча доступна владельцу, **When** он явно выбирает `Поделиться`,
   **Then** открывается одна именованная модалка с фокусом в поле получателя.
2. **Given** внешняя email-доставка выключена, **When** владелец вводит внешний
   адрес, **Then** интерфейс заранее сообщает, что внешнее приглашение пока
   недоступно, сохраняет введённое значение и предлагает допустимую альтернативу
   без общего сообщения «Попробуйте ещё раз».
3. **Given** адрес соответствует активному пользователю текущего workspace,
   **When** владелец выбирает подсказку и отправляет приглашение, **Then** создаётся
   view-доступ по умолчанию с областью `Только итоги`, а список доступа обновляется.
4. **Given** браузерный или embedded-кабинет, **When** выполняется один и тот же
   сценарий, **Then** доступные действия, ошибки, scope и фокусное поведение
   совпадают.

### User Story 2 - Дать получателю полезный и безопасный первый опыт (Priority: P1)

Получатель приглашения понимает, кто поделился встречей и что именно ему
доступно. Открытие одноразовой ссылки сразу запускает безопасное принятие и
переводит его на разрешённый результат. Если у него ещё нет GRAF, личный
аккаунт создаётся внутри этого явного действия, а не скрытым GET-запросом.

**Why this priority**: Вирусность появляется только после полезного первого
опыта. При этом письмо и ссылка не должны раскрывать чувствительное содержимое.

**Independent Test**: Пригласить synthetic external address в режиме доставки,
открыть письмо без содержимого встречи, пройти проверку точного адреса,
открыть страницу записи, проверить summary/transcript/playback/audio download
и combined export. Проверить, что workspace membership не создан без отдельного
согласия, а revoke блокирует страницу и egress на следующем запросе.

**Acceptance Scenarios**:

1. **Given** приглашение отправлено, **When** получатель открывает письмо,
   **Then** он видит имя пригласившего, безопасный заголовок/время встречи,
   область доступа, срок действия, основную кнопку и ссылку на настройки
   уведомлений, но не transcript, audio или summary text.
2. **Given** получатель не вошёл в GRAF, **When** он открывает одноразовую ссылку,
   **Then** страница автоматически отправляет существующий CSRF-bound POST,
   magic link подтверждает приглашённый email, а если аккаунта ещё нет, GRAF
   создаёт personal account автоматически и сразу открывает разрешённую страницу
   записи. При отключённом JavaScript остаётся одна кнопка для того же действия.
   Получатель может просмотреть саммари и транскрипт с таймкодами, послушать
   запись, скачать аудио и сохранить combined export «расшифровка + саммари»;
   отдельные пароль, код и `/sign-up` не требуются.
3. **Given** получатель открыл CTA `Попробовать GRAF`, **When** он завершает
   onboarding, **Then** referral attribution связывает регистрацию с приглашением
   без передачи текста встречи и без автоматического добавления в workspace.
4. **Given** токен просрочен, отозван или открыт не тем подтверждённым адресом,
   **When** получатель обращается к нему, **Then** GRAF показывает общий экран
   недоступности без подтверждения существования встречи.

### User Story 3 - Управлять доступом без матрицы разрешений (Priority: P1)

Владелец видит, кто уже получил доступ, что именно они увидят и когда доступ
истекает. Он может отозвать или обновить доступ, а копирование ссылки не может
случайно сделать встречу публичной.

**Why this priority**: Встречи содержат аудио, transcript и итоги; sharing
должен быть обратимым и соответствовать принципу минимально необходимого
доступа.

**Independent Test**: Создать summary-only и full-meeting grant в синтетических
данных, открыть каждый grant правильным и неправильным пользователем, отозвать,
повторить запрос и проверить блокировку на следующем запросе.

**Acceptance Scenarios**:

1. **Given** владелец открывает Share, **When** он видит первый экран,
   **Then** для внутреннего доступа по умолчанию выбран `Только итоги` и
   `Просмотр`, а email-приглашение записи явно сообщает full package; сложные
   настройки раскрываются только после явного действия.
2. **Given** владелец выбирает `Вся встреча`, **When** он подтверждает изменение,
   **Then** перед сохранением перечислены доступные артефакты: summary,
   transcript, playback, audio download и combined export; запрещённые политикой
   или неготовые артефакты не появляются.
3. **Given** существует recipient-bound grant, **When** владелец копирует ссылку,
   **Then** ссылка сохраняет текущий scope, не расширяет аудиторию и может быть
   отозвана или ротирована.
4. **Given** встреча удаляется или grant отозван, **When** получатель обновляет
   страницу, **Then** новый доступ блокируется внутри GRAF-controlled систем.
5. **Given** письмо уже принято почтовым сервисом, **When** владелец видит статус,
   **Then** текст не обещает доставку во входящие и различает `отправлено`,
   `ожидает`, `истекло`, `отозвано`, `ошибка` и `неизвестный результат`.

### User Story 4 - Найти нужного человека из безопасных источников (Priority: P2)

Владелец может выбрать участника связанного календарного события, известного
пользователя workspace или контакт из явно разрешённой адресной книги. Источник
подсказки виден, а наличие в календаре или адресной книге само по себе не даёт
доступ и не считается согласием на запись.

**Why this priority**: Контактные подсказки сокращают время отправки и делают
приглашение естественным, но полный импорт адресной книги создаёт лишний
privacy-риск и не нужен для первой ценности.

**Independent Test**: Для синтетической встречи подготовить календарный roster,
workspace directory и ограниченный контактный picker. Проверить объединение и
дедупликацию подсказок, отсутствие email неавторизованных людей и корректное
поведение при отключённом источнике.

**Acceptance Scenarios**:

1. **Given** у встречи есть подтверждённый календарный контекст, **When** владелец
   открывает поле получателя, **Then** сначала предлагаются релевантные участники
   с пометкой источника и без создания grant.
2. **Given** источник календаря устарел, недоступен или участник отказался,
   **When** показываются подсказки, **Then** статус источника обозначен честно и
   отсутствующий/отказавшийся участник не становится доступным автоматически.
3. **Given** пользователь выбирает адресную книгу, **When** доступ не выдан,
   **Then** показывается явный native picker/запрос разрешения, а GRAF не загружает
   полный список контактов на сервер.
4. **Given** один человек найден в нескольких источниках, **When** список строится,
   **Then** показывается одна запись с понятным набором источников и одной
   нормализованной identity.

### User Story 5 - Превратить просмотр в добровольное знакомство с GRAF (Priority: P2)

Получатель видит пользу GRAF в самом контексте встречи и может добровольно
попробовать продукт. Владелец получает только агрегированную воронку, которая
помогает понять, работает ли распространение, без слежки за содержанием встречи.

**Why this priority**: Это целевая вирусная механика, но она должна усиливать
полезность sharing, а не превращать встречу в рекламный спам.

**Independent Test**: Пройти synthetic funnel `share opened → invitation sent →
opened → summary viewed → CTA clicked → signup completed`, проверить одну
атрибуцию на приглашение, отсутствие текста встречи и корректное ограничение
повторных/подозрительных событий.

**Acceptance Scenarios**:

1. **Given** получатель успешно посмотрел разрешённые итоги, **When** он видит
   CTA, **Then** CTA объясняет ценность GRAF и не блокирует просмотр/закрытие.
2. **Given** получатель уже имеет GRAF, **When** он открывает summary, **Then**
   приглашение не создаёт второй аккаунт и не запускает повторную воронку.
3. **Given** пользователь повторно открывает одну ссылку или пересылает её,
   **When** воронка собирает события, **Then** повторный просмотр не создаёт
   новый share grant или неограниченный referral credit.
4. **Given** рабочая область выключила external/public sharing, **When** оператор
   откатывает rollout, **Then** новые приглашения/ссылки останавливаются, а
   существующие controlled grants остаются управляемыми и отзывными.

### Viral mechanics portfolio (gated extensions)

Чтобы один пользователь мог естественно распространить GRAF на команду,
система должна поддерживать несколько последовательных петель, а не одну
реферальную кнопку:

1. **Поделиться с участниками** — явное действие владельца для подходящих
   verified workspace participants. Каждый получатель получает отдельный
   summary-only/view-only grant и видит результат в `Shared with me`.
2. **Автоподелиться внутренними итогами** — opt-in правило владельца после
   первого успешного share. Перед включением показывается список получателей,
   а private/1:1 встречу можно исключить одним действием.
3. **Shared with me + onboarding** — получатель открывает полезный summary,
   затем видит ненавязчивый CTA `Подключить GRAF к моим встречам`. CTA не
   блокирует content и не запускает capture без отдельного согласия.
4. **Pre-read повторяющейся встречи** — перед следующей инстанцией recurring
   event текущие разрешённые участники получают ссылку на предыдущий summary и
   незакрытые action items. Это отдельная opt-in настройка, а не silent share.
5. **Workspace team access** — администратор может включить summary-only
   просмотр по роли (`off`, `manager`, `member`). Такая политика не даёт edit,
   share, export или retroactive доступ без отдельного подтверждения.
6. **Action-item loop** — явное назначение action item приводит адресата в GRAF
   по уже разрешённому scope; содержание уведомления минимально и не является
   обходом meeting authorization.
7. **Рабочие каналы и календарь** — будущие Slack/Teams и calendar-pointer
   интеграции доставляют ссылку в привычный workflow, но никогда не создают
   дополнительный grant сами по себе.

Приоритет: сначала `Поделиться с участниками` + `Shared with me`, затем личный
auto-share и recurring pre-read; team access, action-item distribution и
интеграции включаются отдельными операционными и privacy-гейтами. Не входят:
рейтинги пользователей, реферальные бонусы, автоматическое добавление в
workspace, массовая рассылка по календарю и скрытая синхронизация адресной книги.

### Edge Cases

- Пользователь приглашает себя, владельца, уже имеющего доступ пользователя или
  адрес с активным pending invitation.
- Ввод содержит несколько адресов, пробелы, разные регистры, дубли и один
  невалидный адрес среди валидных.
- Поиск по имени неоднозначен; поиск по email совпадает с несколькими
  identity-источниками; адрес относится к другому workspace.
- Внешняя доставка выключена, секрет/почтовый сервис недоступен, отправка
  зависла после принятия запроса или получатель отписался от уведомлений.
- Ссылка истекла, отозвана, ротирована, открыта с неправильным workspace или
  после начала удаления встречи.
- Календарь не подключён, snapshot устарел, attendee скрыт политикой или
  календарный адрес не подтверждён.
- Пользователь отказывает в доступе к Contacts, разрешает только часть
  контактов или нативный picker недоступен в browser-only surface.
- Rate limit достигнут, запросы приходят параллельно в двух вкладках или
  пользователь нажимает Invite несколько раз.
- Ошибка UI/JS или stale page не должна превращать hidden capability в прямой
  обход server authorization.

## Requirements *(mandatory)*

### Functional Requirements

FR-036–FR-042 и SC-017–SC-021 ниже описывают следующий gated design slice. Они
зафиксированы для архитектурной целостности и product review, но не являются
утверждением, что текущий internal-first кандидат уже реализует эти механики.

- **FR-001**: Сервер MUST публиковать для Share отдельные capability и причины
  доступности для internal grant, external invitation, recipient-bound link и
  public link.
- **FR-002**: UI MUST показывать только действия, разрешённые текущими
  capability, и MUST открывать Share только после явного действия пользователя.
- **FR-003**: Browser и embedded cabinet MUST использовать одну и ту же модель
  состояния, policy и copy для Share.
- **FR-004**: Первый экран MUST отвечать на вопросы «кому дать доступ?» и «что
  он увидит?» через поле получателя, подсказки, `Пригласить` и свёрнутый
  summary-only scope.
- **FR-005**: По умолчанию новый доступ MUST быть invite-only, view-only и
  `Только итоги`.
- **FR-006**: В gated email path система MUST поддерживать ввод одного или
  нескольких нормализованных email/identity с чипами, дедупликацией и адресными
  ошибками. В первой internal поставке допускается одна явно выбранная identity
  за действие, но повторный выбор того же получателя MUST быть подавлен.
- **FR-007**: Поиск MUST возвращать только активные identity, которые текущий
  владелец имеет право увидеть в текущем workspace и в рамках конкретной
  meeting, для которой у него есть `can_share`; endpoint MUST принимать meeting
  context, экранировать wildcard-символы и не должен подтверждать наличие чужой
  private identity.
- **FR-008**: При выключенной external delivery система MUST не отправлять
  сетевой запрос на приглашение и MUST показывать объяснение с допустимой
  альтернативой, если она существует.
- **FR-009**: Email invitation MUST иметь bounded lifecycle: pending, sending,
  sent, accepted, expired, revoked, failed или outcome-unknown; повторная отправка
  не должна происходить автоматически после неоднозначного сетевого результата.
  Принятый grant MUST наследовать срок invitation или иметь другой явно bounded
  срок, но не становиться бессрочным.
- **FR-010**: Получатель MUST подтвердить именно приглашённый адрес до выдачи
  grant; для external invitation это делает одноразовый magic link. GET исходной
  ссылки не должен создавать account, выдавать grant или добавлять пользователя
  в workspace; эти действия выполняются только существующим CSRF-bound POST,
  который автоматически отправляется браузером после открытия ссылки или
  запускается одной fallback-кнопкой при отключённом JavaScript.
- **FR-011**: Система MUST различать доступ к summary и full meeting; полный
  scope может быть выбран только явно и только если policy и готовность артефактов
  его разрешают.
- **FR-012**: View access MUST быть отдельным от download/export; первая Share
  поверхность не должна показывать capability matrix.
- **FR-013**: Владелец MUST видеть текущие grants и pending invitations, а также
  отзывать grant/invitation, менять scope по разрешённым правилам и видеть срок.
- **FR-014**: Copy link MUST сохранять текущую аудиторию и scope; recipient-bound
  link не должен становиться public или workspace-wide побочным эффектом.
- **FR-015**: Link grants MUST поддерживать срок действия, rotation и revoke;
  public links MUST оставаться выключенными по умолчанию и gated policy.
- **FR-016**: Каждый запрос к meeting, summary, transcript, playback, export и
  download MUST повторно проверять authorization, scope, lifecycle и deletion
  state на сервере.
- **FR-017**: Ошибки unauthorized, expired, wrong-recipient, deleted и
  not-found MUST быть privacy-preserving и не раскрывать private title,
  participants, transcript, audio, summary или наличие чужой identity.
- **FR-018**: Share mutation, invitation delivery, link open, grant view, revoke,
  scope change и referral events MUST иметь metadata-only audit evidence без
  transcript, audio, credentials, raw tokens или private meeting content.
- **FR-019**: Email MUST содержать только безопасные meeting metadata, inviter,
  scope, expiry, действия входа/создания аккаунта и настройки уведомлений; raw
  transcript/audio/summary text и tracking pixel для meeting content запрещены.
- **FR-020**: Recipient surface MUST показывать разрешённый content после
  успешной проверки exact identity, но CTA не должен требовать workspace join.
  Открытие одноразовой ссылки запускает автоматическое действие принятия; при
  отключённом JavaScript остаётся `Открыть итоги` для `summary_only` или
  `Открыть запись` для `full_meeting`. Явное действие может создать только
  personal account для приглашённого адреса.
- **FR-021**: Referral attribution MUST использовать opaque bounded identifier,
  быть одноразово привязанной к invitation/grant и не помещать meeting content,
  email или raw token в URL, analytics или клиентское хранилище.
- **FR-022**: Система MUST фиксировать агрегированные funnel events минимум для
  открытия Share, выбора получателя, запроса приглашения, открытия, успешного
  просмотра, CTA и signup; событие не должно содержать текст встречи.
- **FR-023**: Rate limits, cooldown, duplicate suppression и abuse gate MUST
  ограничивать массовые приглашения, повторные открытия и подозрительные ссылки
  на уровне owner/workspace/source, включая recipient/contact search и link
  rotation, не раскрывая пользователю private account existence. Публичный link
  MUST проверять effective abuse gate при каждом создании и разрешении, а не
  только при загрузке конфигурации.
- **FR-024**: Calendar suggestions MUST использовать только текущий
  user-authorized calendar context, показывать источник и не превращать attendee
  в grant или consent автоматически.
- **FR-025**: Contact suggestions MUST объединять workspace directory,
  meeting-calendar participants и явно разрешённый contact source с
  детерминированной дедупликацией по подтверждённой identity.
- **FR-026**: Address-book lookup MUST начинаться с native/least-privilege
  picker или эквивалентного явного разрешения; полный address-book sync и
  постоянное хранение не входят в первую поставку.
- **FR-027**: Если источник контактов отключён, устарел, denied или недоступен,
  UI MUST показать bounded state и сохранить рабочим typed email path, если
  внешняя delivery policy разрешена.
- **FR-028**: Share modal MUST поддерживать visible focus, keyboard-only
  navigation, Escape только для безопасного закрытия transient UI, focus return,
  live-region status, Russian accessible names, reduced motion, increased
  contrast и narrow viewport без горизонтального скролла.
- **FR-029**: Политика external/public sharing MUST иметь явные operator gates
  для доставки, identity verification, rate limiting, abuse, retention,
  deletion, audit и legal copy; выключенная capability не должна быть доступна
  через прямой запрос. Raw share/invitation/referral tokens MUST не попадать в
  application/proxy logs, analytics, referrer и browser-autocapture; token URL
  MUST отдавать no-store/no-referrer/noindex защитные заголовки или короткий
  server-side exchange.
- **FR-030**: Начало deletion MUST немедленно блокировать новые grants,
  invitations, link opens, egress и referral publication внутри GRAF; copy MUST
  обещать удаление только в пределах контроля GRAF и честно описывать retained
  observability history согласно продуктовой политике.
- **FR-031**: Rollout MUST быть обратимым: отключение новых capabilities
  прекращает новые действия без удаления audit history, а действующие grants
  остаются отзывными и подчиняются текущей authorization/deletion truth.
- **FR-032**: Фича MUST reuse existing meeting access, email delivery, audit,
  calendar, deletion и export authorities и не создавать параллельные источники
  правды.
- **FR-033**: UI MUST отображать `sent` как принятие почтовым сервисом, а не как
  подтверждение доставки во входящие; для ошибки после сетевого egress должен
  существовать bounded outcome-unknown state.
- **FR-034**: Validation evidence MUST использовать synthetic names, addresses,
  meetings and content; реальные письма, transcript, audio, tokens и private
  contact records не должны попадать в git или evidence.
- **FR-035**: Domain service MUST повторно обеспечивать audience, content scope,
  download/export, expiry и deletion invariants независимо от API schema; одна
  обходная точка не должна создавать external/full/public grant с некорректной
  комбинацией.
- **FR-036**: Внутренний режим `share_with_meeting_participants` MUST создавать
  отдельные summary-only/view-only grants только для verified active workspace
  identities текущего meeting roster; owner, declined/hidden, external и
  unknown attendees MUST быть исключены.
- **FR-037**: Личная политика auto-share MUST быть opt-in, показывать preview
  аудитории, поддерживать private/1:1 override и не распространять full,
  external или public scope.
- **FR-038**: `Shared with me` MUST показывать только уже выданные grants,
  сохранять scope/expiry/revoke truth и предлагать onboarding CTA без
  автоматического signup, workspace join или запуска capture.
- **FR-039**: Pre-read для recurring meeting MUST вычислять текущую допустимую
  аудиторию для каждой инстанции, не выдавать доступ задним числом и не включать
  transcript/audio в уведомление.
- **FR-040**: Workspace team access MUST иметь отдельный admin gate и роль,
  ограничиваться summary/view, не давать edit/share/export и требовать явного
  подтверждения для ретроактивного применения.
- **FR-041**: Action-item, calendar-pointer, Slack и Teams distribution MUST
  использовать существующий grant/authorization слой; доставка ссылки или
  action item не может сама создать или расширить доступ.
- **FR-042**: Adoption analytics MUST измерять переход от eligible recipient к
  summary view, CTA, setup и first own capture metadata-only и bounded образом;
  meeting content, email, raw token и индивидуальное поведение вне GRAF
  controlled surface запрещены.

### Key Entities *(include if feature involves data)*

- **Share Capability**: Серверное описание доступных аудиторий, scope, действий,
  rollout-флагов и пользовательской причины отказа.
- **Meeting Access Grant**: Связанный с одной встречей и workspace grant для
  identity, workspace или явно разрешённой link-аудитории со scope, status,
  expiry, rotation и revoke truth.
- **Share Invitation**: Одноразовое/ограниченное по времени приглашение с
  нормализованным hash адреса, bounded delivery state, grant scope и audit
  lifecycle; raw delivery secret не является UI-данными.
- **Contact Suggestion**: Эфемерная или bounded view-модель кандидата с
  display label, разрешённым способом связи, источником, freshness и
  confidence; suggestion не равна grant.
- **Contact Source**: Авторизованный календарь, workspace directory или
  явный address-book provider/picker с owner scope, permission state и sync
  freshness.
- **Referral Attribution**: Opaque bounded связь между invitation/grant и
  добровольными onboarding/funnel событиями без meeting content.
- **Share Audit Event**: Metadata-only запись запроса, изменения policy,
  delivery, просмотра, revoke и referral transition.
- **Share Rollout Policy**: Operator-controlled capability, TTL, rate limit,
  abuse, delivery, identity, retention и rollback gates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: В synthetic regression для каждого выключенного capability 100%
  недоступных действий отсутствуют в UI или показывают объяснённое состояние,
  и 0 недоступных запросов уходит на сервер из Share modal.
- **SC-002**: Владелец, впервые открывающий Share, может отправить внутреннее
  summary-only приглашение не более чем за 30 секунд и максимум за 3 явных
  действия после ввода получателя.
- **SC-003**: 100% сценариев `pending`, `sent`, `accepted`, `expired`, `revoked`,
  `failed` и `outcome-unknown` имеют различимые user-facing состояния и
  bounded next action.
- **SC-004**: В 100% проверок revoked, expired, wrong-recipient и deleting
  access блокируется на следующем GRAF-controlled запросе без утечки private
  metadata.
- **SC-005**: В synthetic email/evidence scan 0 transcript, audio, summary text,
  raw token, credential, private path и live contact record попадает в письмо,
  analytics, audit, logs, screenshots или committed evidence.
- **SC-006**: Не менее 95% валидных synthetic recipient queries из разрешённых
  источников дают подсказки или объяснённый empty state не позднее 1 секунды
  после ввода; источник и freshness видимы пользователю.
- **SC-007**: В 100% contact-source сценариев наличие attendee/contact без явного
  подтверждения владельца не создаёт grant и не меняет consent/recording state.
- **SC-008**: В synthetic funnel каждое приглашение имеет не более одной
  attributed signup conversion, а повторные открытия не создают новые grants,
  accounts или unlimited referral credit.
- **SC-009**: Rate-limit и abuse tests блокируют превышение заданных лимитов,
  сохраняя privacy-preserving response и возможность оператора отключить
  external/public capability одним rollout change.
- **SC-010**: Browser и embedded surfaces проходят один и тот же acceptance
  matrix для capability, scope, error, revoke, link, keyboard, VoiceOver,
  reduced motion, increased contrast, dark/light и narrow viewport.
- **SC-011**: Rollback rehearsal останавливает новые external/public actions
  без потери metadata-only audit trail и без появления обходного прямого пути.
- **SC-012**: После завершения Share flow не менее 90% synthetic reviewers
  правильно называют, кто получил доступ, какой scope выдан и как его отозвать.
- **SC-013**: 100% recipient-search запросов без конкретной разрешённой meeting
  или без `can_share` возвращают bounded отказ/пустой результат и не дают
  directory enumeration.
- **SC-014**: В 100% synthetic invitation acceptance тестов срок созданного
  grant не превышает срок invitation; после expiry доступ блокируется на
  следующем запросе.
- **SC-015**: В synthetic log, header, analytics и browser-history checks 0 raw
  share/invitation/referral tokens обнаруживаются вне специально разрешённого
  одноразового exchange.
- **SC-016**: Synthetic abuse tests подтверждают bounded response для поиска,
  выдачи, rotation, acceptance и public resolution; оператор может выключить
  каждый gated capability независимо.
- **SC-017**: В synthetic meeting с несколькими подходящими внутренними
  участниками владелец может одним явным действием создать grants всем выбранным
  участникам, а каждый grant остаётся индивидуально отзывным.
- **SC-018**: В 100% participant-share тестов declined, hidden, external и
  unknown attendees не получают grant, delivery record или referral event.
- **SC-019**: В synthetic adoption funnel один просмотренный summary может
  привести максимум к одной signup/first-setup attribution на recipient, а
  повторные открытия не создают новые grants или accounts.
- **SC-020**: Auto-share, pre-read и team access имеют отдельные off/opt-in/
  rollback states; отключение прекращает новые действия без обхода текущей
  revoke/deletion truth.
- **SC-021**: В synthetic channel/calendar distribution 0 сообщений или
  calendar pointers расширяют authorization; они содержат только разрешённую
  ссылку и metadata-only copy.

## Assumptions

- Existing server-side access, audit, email delivery, calendar, deletion and
  egress authorities remain the source of truth and are reused.
- Internal workspace sharing can be enabled independently from external email
  delivery and public links.
- External invitations and public links remain feature-flagged off in the
  default production profile until their delivery, abuse, identity, legal,
  retention and deletion gates are explicitly accepted.
- Calendar attendees are discovery hints, not proof of consent, identity or
  access permission; owner must choose each recipient.
- Address-book v1 uses explicit native/least-privilege selection where a native
  surface exists. Provider-level Google/Microsoft contact search is a later
  opt-in source with delegated read-only scopes and bounded caching.
- The first viral loop is value-led onboarding and transparent attribution, not
  discounts, rewards, auto-follow, auto-join or bulk email.
- The strongest adoption loop is participant distribution: one useful summary
  creates the next potential GRAF user. Participant auto-share is therefore a
  separate explicit opt-in policy, not an invisible default for every meeting.
- Russian dark UI remains primary; light theme, browser and embedded parity are
  required acceptance surfaces.
- GRAF-controlled deletion does not claim universal erasure from operator-managed
  observability systems; deletion copy follows the existing product gate.
