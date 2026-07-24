# Research: Обмен встречами и поиск получателей

**Feature**: [spec.md](spec.md)
**Date**: 2026-07-23

## 1. Подтверждённая причина текущего сбоя

### Decision

Share должен получать и показывать capability-состояния с сервера. Внешнее
приглашение не должно быть доступно в модалке, пока
`share_external_invitations_enabled` выключен. Если устаревший клиент всё же
отправил запрос, сервер сохраняет fail-closed ответ с кодом политики, а клиент
показывает этот код как понятное следующее действие. В текущем controlled
rollout флаг планируется true только для exact-email summary-only приглашений;
public links, contacts и referral остаются false.

### Evidence

- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` после
  пустого результата поиска всегда делает POST во внешний invitation endpoint,
  если строка содержит `@`.
- `apps/server/src/twobrain_rec_server/api/cabinet.py` возвращает 403 с кодом
  `share_invitations_disabled`, когда флаг внешней доставки выключен.
- `apps/server/src/twobrain_rec_server/config.py` выключает внешний путь по
  умолчанию и валидирует его зависимые delivery/Temporal/secret/base-url gates.
- Клиент выбрасывает только HTTP status и заменяет problem code на общий текст
  «Не удалось пригласить», поэтому пользователь не видит, что действие
  запрещено политикой.
- Внутренний grant API возвращает `share_url`, но текущий JS его игнорирует, а
  fragment не показывает Copy link.

### Rejected alternatives

- Включить внешний email-путь только для того, чтобы кнопка перестала ошибаться:
  отвергнуто — это обходит уже существующие delivery, identity, abuse, legal и
  deletion gates.
- Считать любой адрес с `@` внутренним пользователем: отвергнуто — identity
  принадлежит GRAF, а не строке в поле.
- Оставить общий текст ошибки: отвергнуто — он не объясняет, что делать дальше,
  и маскирует системное состояние.

## 2. Модель доступа и поверхность модалки

### Decision

Разделить три независимых вопроса:

1. **Кто** получает доступ: активный пользователь workspace, адресат
   внешнего приглашения или link-аудитория.
2. **Что** получает: `Только итоги` по умолчанию; `Вся встреча` только после
   явного подтверждения и только при готовом policy gate.
3. **Что может сделать** получатель: просмотр отдельно от download/export.

Первый экран остаётся коротким: получатель, видимый scope summary-only, список
текущего доступа, inline-состояние capability. Сложные настройки не должны
превращать Share в permission matrix.

### Reference findings

- Krisp разделяет Summary/Everything, invite-only/workspace/anyone-link и даёт
  владельцу просмотр и отзыв доступа. Его календарное автоподеление полезно как
  discovery pattern, но для GRAF небезопасно как default.
- Read.ai разделяет access к отчёту и distribution по email/Slack/Teams; у
  получателя есть viewer/editor и revoke. Это подтверждает, что «доступ» и
  «уведомить» должны быть разными решениями.
- Fathom показывает named people, same-domain и anyone-link, а также summary-only
  вариант. При этом автоподеление всем календарным гостям и бессрочный/широкий
  link-flow требуют более сильной политики, чем доступна GRAF сейчас.
- Fireflies и Otter подтверждают полезность expiry, явных групп/адресатов,
  ролей и revoke; permissive public links и неотзываемые ссылки не подходят для
  встреч с аудио и transcript.

### Rejected alternatives

- Автоматически делиться со всеми календарными attendee: отвергнуто — наличие
  attendee не является согласием на доступ к записи.
- Показывать на первом экране полную матрицу ролей/download/export: отвергнуто —
  повышает вероятность ошибочного egress и ухудшает первый share path.
- Ставить `Anyone with the link` рядом с обычным Invite по умолчанию:
  отвергнуто — public link остаётся отдельным operator-gated режимом.

## 3. Вирусная механика

### Decision

Вирусный цикл строится вокруг полезного первого результата:

`получатель → безопасное письмо/CTA → единый email/provider-вход →
автоматический personal account при первом входе → summary-only просмотр →
ненавязчивый «Попробовать GRAF»`.

CTA не блокирует просмотр и не добавляет человека в workspace автоматически.
Первый email/provider-вход может создать personal account только как явное
действие получателя. Attribution — только непрозрачный bounded id,
одноразово связанный с invitation/grant; в событии нет title, transcript,
summary text, email или raw token. На первом этапе достаточно metadata-only
событий и существующего product-analytics gate; новая внешняя аналитическая
зависимость не нужна.

### Reference findings

- Read.ai показывает путь от shared report к signup, но аккаунт появляется
  только после действия получателя. Для GRAF это реализуется одним auth-шагом:
  email-код может создать personal account автоматически, без отдельной
  registration-страницы.
- Письмо Krisp содержит безопасные metadata встречи и кнопку просмотра, но не
  встраивает transcript или summary text. Этот принцип снижает утечку через
  пересылку письма и preview в почтовом клиенте.
- Fathom/Fireflies показывают ценность прямо в recap/share context; GRAF должен
  использовать ценность summary, а не скидки, награды или spam-механику.

Дополнительные практики, которые нужно перенести аккуратно:

- Krisp делает auto-share только после календарного match, подавляет duplicate
  email, если одну встречу записали несколько пользователей, и пропускает
  неоднозначные overlapping meetings. Для GRAF это аргумент в пользу
  canonical distribution run, а не простого цикла по attendee.
- Fathom разделяет `Summary Only` и `Summary & Recording`, но отправляет
  auto-share всем приглашённым календарём даже если человек не пришёл и не умеет
  полностью «unsend» уже доставленное содержимое. GRAF должен выбрать более
  безопасное правило: internal verified roster, summary-only default и preview
  до auto-share.
- Fireflies использует явные presets `Only Owner`, `Teammates`, `Participants`
  и `Teammates & Participants`, поддерживает Shared with Me и expiry. Это
  хороший язык режимов, но public/link access не должен быть дефолтом GRAF.
- Otter умеет приглашать пользователей того же домена в workspace при share.
  Для GRAF это может быть будущим SSO/onboarding путём, но membership должен
  создаваться только после явного согласия получателя.

Источники: [Krisp auto-share](https://help.krisp.ai/hc/en-us/articles/10386573495196-Sharing-your-meetings-with-Krisp),
[Krisp Teams distribution](https://help.krisp.ai/hc/en-us/articles/26704048673436-Integrate-Krisp-with-Microsoft-Teams),
[Fathom auto-share](https://help.fathom.video/en/articles/7574785),
[Fathom internal attendees](https://help.fathom.video/en/articles/5750273),
[Fireflies privacy modes](https://guide.fireflies.ai/articles/2474667467-share-meeting-recaps-with-teammates-participants-specific-people-user-groups-and-non-fireflies-users),
[Otter workspace invite](https://help.otter.ai/hc/en-us/articles/7377633500183-Invite-people-to-your-Workspace-through-sharing-a-conversation).

### Что объясняет быстрый рост Read.ai в компании

Наблюдение пользователя похоже не на классическую referral-программу, а на
distribution-by-default: один человек создаёт полезный артефакт, а участники
встречи получают повод открыть его и включить тот же workflow для своих встреч.
В актуальной документации Read.ai есть три усиливающих петлю паттерна:

1. отчёт может автоматически открываться приглашённым участникам, если владелец
   не сделал встречу private;
2. workspace может включить отдельный Team Report Access с ограничением роли;
3. recap, pre-read перед следующей встречей, ссылка в событии календаря и
   сообщения в Slack/Teams доставляют ценность туда, где команда уже работает.

Источники: [автоматический доступ участникам](https://support.read.ai/hc/en-us/articles/23219401248019-How-do-I-control-meeting-report-sharing-and-distribution),
[Team Report Access](https://support.read.ai/hc/en-us/articles/23050745830163-How-can-I-automatically-share-reports-with-my-Team-Team-Report-Access),
[настройка private report](https://support.read.ai/hc/en-us/articles/40479237381011-How-do-I-make-my-meeting-reports-private),
[доставка в Slack](https://support.read.ai/hc/en-us/articles/23833861958419-How-can-I-share-meeting-reports-to-Slack).

### Портфель вирусных механик для GRAF

| Механика | Как возникает петля | Приоритет и безопасная граница |
|---|---|---|
| **Итоги всем подходящим участникам** | Владелец одним действием выбирает «Поделиться с участниками»; каждый внутренний участник видит summary в `Shared with me` и получает CTA включить GRAF для своих встреч. | P0. Только verified workspace identities, `summary_only/view_only`, исключить owner, declined/hidden/external/unknown; сначала явное действие, затем личная opt-in настройка. |
| **Автоподелиться внутренними итогами** | После первого успешного share GRAF предлагает владельцу включить правило для следующих встреч. Это превращает каждую новую встречу в новый вход для команды. | P1. Opt-in владельца или workspace policy; private override на встрече; никаких external/full grants; отдельный preview списка получателей. |
| **Лента «Доступно мне»** | Получатель не теряет ссылку в почте: новый summary появляется в его рабочем списке с именем автора, временем, scope и CTA. | P0. Лента показывает только уже выданный доступ, не расширяет аудиторию и не раскрывает чужие meetings. |
| **Pre-read для повторяющейся встречи** | Перед следующей встречей участники получают предыдущие action items/open questions и ссылку на разрешённый summary; GRAF становится частью ритуала встречи. | P1. Только для recurring event, текущего roster и существующих grants; без transcript/audio в уведомлении; отдельный opt-in и отключение для 1:1/private. |
| **Workspace team access** | Один пользователь подключает GRAF, а команда начинает видеть безопасные итоги коллег без ручного invite каждого человека. | P1. Только admin-gated, по ролям `off/manager/member`; view-only summary, без edit/share/export; не применять задним числом без подтверждения. |
| **Action-item loop** | Назначенный action item приводит коллегу в GRAF, где он видит контекст и может включить GRAF для собственных встреч. | P1. Только явно назначенный получатель; в push/email — metadata и ссылка, не чувствительный текст; external delivery остаётся gated. |
| **Calendar pointer** | Владелец по желанию добавляет в событие календаря ссылку на GRAF summary; участники находят результат там же, где живёт встреча. | P2. Только link/pointer, без записи summary в календарь; доступ всё равно проверяется сервером; никаких скрытых изменений события. |
| **Slack/Teams distribution** | Recap приходит в рабочий канал или DM и приводит новых пользователей в GRAF. | P2. Интеграция отдельным gate; сообщение не создаёт доступ, а работает только для уже разрешённой аудитории или канала с явной политикой. |
| **Мягкий social proof** | После нескольких просмотров показывается «В вашей команде уже используют GRAF» и предложение настроить свои встречи. | P2. Только агрегированные counts после минимального порога, без рейтингов, имён и давления; не считать отправленные письма adoption. |

### Team Library как усилитель после Shared with me

У похожих продуктов заметен отдельный паттерн team library/shared collection:
Fathom использует Team Library/Folders, Otter — Channels, tl;dv — Team
Libraries, Grain — Teams. Это не просто список входящих ссылок: команда получает
устойчивое место, где разрешённые рабочие записи можно находить повторно.

Для GRAF это сильнее, чем универсальный `workspace`-grant, по трём причинам:

- библиотека даёт повторяемую ценность после первого просмотра;
- scope можно задать коллекции/роли, а не всей компании;
- owner private override и membership-loss остаются проверяемыми.

Но в текущей модели нет canonical team directory и сущности коллекции. Поэтому
P0 — только `Shared with me`; Team Library — отдельный P1 после определения
команд, ролей, владельца коллекции и правил retroactive access. Нельзя
эмулировать её через `workspace` audience или показывать всем активным членам
workspace.

Источники: [Fathom Team Library](https://help.fathom.video/en/articles/295808),
[Otter Channels](https://help.otter.ai/hc/en-us/articles/360049379794-Channels-Overview),
[tl;dv Team Libraries](https://intercom.help/tldv/en/articles/15033894-team-libraries),
[Grain Teams](https://support.grain.com/en/articles/12258151-teams).

### Рекомендуемая последовательность

Главная петля GRAF должна быть:

`записал встречу → поделился итогами с внутренними участниками → участник открыл
Shared with me → увидел пользу → включил GRAF для своих встреч → его встреча
создала следующий круг получателей`.

Первый релиз механики — явная кнопка «Поделиться с участниками» и Shared with
me. После подтверждённой ценности можно включать personal auto-share. Team
access, pre-read, action items и integrations идут отдельными rollout-гейтами.
Так мы получаем эффект распространения Read.ai без неожиданной раздачи всех
встреч всей компании.

Метрики должны измерять не объём рассылки, а переход ценности:
`eligible participant → summary viewed → CTA clicked → own GRAF setup → first
own capture`. Все события metadata-only; title, transcript, audio, summary text,
email и raw token запрещены.

### Уточнения после security review

Participant distribution нельзя реализовать как цикл обычных single-share POST:
при потере ответа retry может повторно изменить grant или выдать новый bearer
URL. До batch rollout нужен один из двух вариантов:

1. bounded distribution operation/idempotency authority, которая хранит только
   fingerprint запроса, per-recipient outcome и безопасный replay result;
2. batch без bearer URL, где авторизация живёт в `Shared with me`, а явное
   копирование ссылки остаётся отдельной single-recipient операцией.

В обоих вариантах retry не вращает токен и другой payload с тем же ключом даёт
`409`. Кроме того, delivery state должен различать подтверждённый отказ и
`outcome_unknown`, invitation token должен быть одноразовым exchange material,
а active membership, calendar-source owner, rate limits и deletion должны
проверяться на сервере перед каждым изменяющим действием/egress. Эти условия не
отменяют viral portfolio; они определяют порядок его включения.

Rate-limit bucket для share-действия сохраняется в отдельной короткой
транзакции: бизнес-транзакция может откатиться, а попытка всё равно должна
учитываться как расход лимита. Scope bucket составляют workspace, actor/device и
тип действия; в bucket не попадают title, email, transcript, audio или token.
Для accept owner workspace используется намеренно — это контекст встречи и
гранта, тогда как actor/device отделяют вызывающего пользователя и устройство.

### Rejected alternatives

- Реферальные бонусы, gamification и авто-follow: отвергнуто — не нужны для
  проверки ценности и создают incentive abuse.
- Pixel или content-based tracking в письме: отвергнуто продуктовой политикой.
- Невидимо создать аккаунт по email: отвергнуто. В invite-flow допускается
  создание personal account только после явного перехода по приглашению и
  подтверждения email/provider-входа.

## 4. Контактные источники

### Decision

Источники объединяются, но suggestion никогда не равен grant:

1. **Workspace directory** — активные identity, которые владелец вправе видеть;
   поиск по имени и разрешённому email identity.
2. **Связанное событие календаря** — только текущий user-authorized snapshot;
   сначала показываются участники, которые можно безопасно сопоставить с
   активной GRAF identity. Остальные attendee не получают доступ автоматически.
3. **Адресная книга** — в первой поставке только явный native/least-privilege
   picker на платформе, где это возможно. Browser-only surface предлагает
   typed email и не делает полный серверный импорт. Provider-level Google/
   Microsoft lookup — отдельный opt-in после согласования scopes и retention.

### Privacy and platform findings

- Apple Contacts требует явного разрешения и поддерживает ограниченный выбор;
  приложение не должно молча выгружать весь store.
- Google People разделяет `contacts.readonly`, `contacts` и directory scopes;
  использовать минимальный read-only scope, а directory scope не запрашивать у
  обычного пользователя.
- Microsoft Graph разделяет delegated `Contacts.Read` и directory permissions;
  расширенный directory доступ не нужен для первого сценария.
- Google Calendar attendee — email/participation metadata, а не authorization
  на раздачу записи.

### Rejected alternatives

- Постоянно хранить полный address book в GRAF: отвергнуто — избыточная PII и
  retention/deletion поверхность.
- Показывать неизвестного attendee как подтверждённого GRAF user: отвергнуто —
  нельзя смешивать календарную identity и учетную запись.
- Использовать календарное присутствие как consent: отвергнуто.

## 5. Системная модель и угрозы

### Assets

- Авторизация на meeting, summary, transcript, playback и egress.
- Email delivery secret, invitation token и verified recipient identity.
- Metadata-only audit и bounded referral state.
- Calendar/contact PII и workspace membership.

### Threats and controls

| Угроза | Контроль |
|---|---|
| UI вызывает выключенный external/public capability | Server capability projection, hidden/disabled UI, повторная server authorization |
| Пересылка invitation другому человеку | exact verified address hash перед grant; generic unavailable response |
| Brute force токенов и массовая рассылка | opaque tokens, TTL, durable delivery fence, owner/workspace/source rate limits, abuse gate |
| Calendar/contact превращается в доступ | candidate-only projection и явное действие владельца |
| Ошибка после SMTP egress | `outcome-unknown`, запрет автоматического повторения |
| Утечка transcript через письмо/analytics | metadata-only payload, forbidden-field validation, synthetic evidence |
| Отзыв не блокирует старый link | серверная проверка status/expiry/deletion на каждом запросе, rotation/revoke |
| Обход через прямой API | capability flags не являются authorization; mutation повторно проверяет meeting access и policy |

### Decision

Использовать уже существующие access/grant/invitation/Temporal/email/audit/
deletion authorities. Новая таблица в первой поставке не нужна. Referral
storage и external provider sync остаются отдельным gate, пока не появится
конкретный approved contract.

## 6. Security blockers

### Обязательные blockers перед rollout

Read-only threat-model review Feature 125 выявил несколько блокеров, которые
нельзя прятать за UI-флагом:

- в baseline accepted invitation не переносил `expires_at` в созданный grant;
- в baseline recipient search не был привязан к meeting и `can_share`, а `%`/`_` могли
  расширять `ILIKE`-поиск;
- для share search, invite creation, link resolution, rotation и acceptance не
  найдено эффективного application-level throttling;
- bearer tokens находятся в URL path и требуют redaction/no-store/no-referrer
  политики;
- часть scope/audience safety invariants защищена только Pydantic schema, а не
  доменным сервисом/единой policy-функцией;
- public-link abuse gate проверяется при построении Settings, но должен быть
  частью effective policy и при resolve;
- post-egress delivery timeout должен быть отличим от подтверждённого provider
  failure и не должен автоматически дублировать письмо.
- internal grant должен проверять active workspace membership при каждом
  доступе, иначе удалённый участник может сохранить доступ через старую строку;
- calendar candidate должен быть привязан к active source владельца встречи, а
  не только к snapshot/link, иначе suggestion может пересечь границу private
  calendar ownership;
- invitation token должен быть одноразовым exchange material и не становиться
  долговременным bearer token accepted grant после acceptance;
- public-link open должен иметь отдельную metadata-only audit evidence, а не
  только обновлять `last_used_at`.

Эти пункты добавлены в FR-007, FR-009, FR-016, FR-023, FR-029 и FR-035 и стали
частью Phase 0/Phase 1 gates. В текущем локальном кандидате перенос expiry,
meeting binding, wildcard escaping, scope checks, public abuse-gate recheck и
token-safe headers закрыты кодом и synthetic tests. Application-level
throttling, first-class delivery `outcome-unknown`, one-time invitation
exchange, membership-loss enforcement и calendar-source ownership закрыты
кодом и synthetic evidence для exact-email/internal пути. Public-open audit,
contact/referral rollout и широкое participant distribution остаются
незакрытыми. Поэтому только exact-email путь объявлен готовым; public/contact/
referral rollout не следует включать на основании одного feature flag.

### Rollout evidence — 2026-07-24

- Postal delivery is server-only, uses a generated persistent HMAC identity
  secret and a separate credential-encryption key; no secret is passed to the
  browser or desktop client.
- Invitation delivery commits a `sending` fence before network egress. Provider
  acceptance becomes `sent`; pre-egress/config failure becomes `failed`; timeout,
  5xx or malformed provider response becomes `outcome_unknown` and is not
  automatically resent.
- Durable actor/device invitation throttling is 10 attempts per workspace and
  device per hour; duplicate active invitations are fenced by the meeting,
  normalized identity hash and partial unique index.
- Token URL/log/referrer protections, exact verified-recipient acceptance,
  bounded grant expiry and revoke/deletion rechecks are covered by contract and
  integration evidence. The local suite uses a synthetic transport; no live
  email was sent without an explicitly consented test recipient. Public links,
  native Contacts/provider lookup and referral attribution remain disabled.
- Production deploy `cffcfb86cd3edbdb91cc37e8f1e0b8c04bd39d66` passed the API and
  delivery-worker config gates, public health checks, Postal network reachability
  check, backup/restore rehearsal and rollback readiness. Exact-email is enabled;
  public/contact/referral capabilities remain independently gated.

## 7. Источники

### Локальные источники

- `docs/prd-voice-layer-final.md`
- `docs/current-product-status.md`
- `specs/125-meeting-sharing/scenarios.md`
- `specs/017-access-sharing-downloads/`
- `specs/121-recording-workflows/`
- `apps/server/src/twobrain_rec_server/cabinet/access.py`
- `apps/server/src/twobrain_rec_server/api/cabinet.py`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html`

### Внешние reference pages

- [Krisp: Sharing your meetings](https://help.krisp.ai/hc/en-us/articles/10386573495196-Sharing-your-meetings-with-Krisp)
- [Krisp: Invite to collaborate after meetings](https://help.krisp.ai/hc/en-us/articles/13674542517660-Invite-to-collaborate-after-meetings)
- [Read.ai: Manage access to an existing report](https://support.read.ai/hc/en-us/articles/23834622441875-How-can-I-manage-access-to-an-existing-report)
- [Read.ai: Report sharing and distribution](https://support.read.ai/hc/en-us/articles/23219401248019-How-do-I-control-meeting-report-sharing-and-distribution)
- [Read.ai: Team Report Access](https://support.read.ai/hc/en-us/articles/23050745830163-How-can-I-automatically-share-reports-with-my-Team-Team-Report-Access)
- [Read.ai: Make reports private](https://support.read.ai/hc/en-us/articles/40479237381011-How-do-I-make-my-meeting-reports-private)
- [Read.ai: Share reports to Slack](https://support.read.ai/hc/en-us/articles/23833861958419-How-can-I-share-meeting-reports-to-Slack)
- [Read.ai: Creating an account from a shared report](https://support.read.ai/hc/en-us/articles/41295760641171-A-Step-by-Step-Guide-on-Creating-a-Read-AI-Account)
- [Fathom: Share meetings](https://help.fathom.video/en/articles/295616)
- [Fathom: Automatically share meetings](https://help.fathom.video/en/articles/7574785)
- [Fireflies: Share meeting recaps](https://guide.fireflies.ai/articles/2474667467-share-meeting-recaps-with-teammates-participants-specific-people-user-groups-and-non-fireflies-users)
- [Otter: Share a conversation](https://help.otter.ai/hc/en-us/articles/360048338793-Share-a-conversation)
- [Apple Contacts: Accessing the contact store](https://developer.apple.com/documentation/contacts/accessing-the-contact-store)
- [Apple ContactsUI](https://developer.apple.com/documentation/ContactsUI)
- [Google People: Contacts API migration/scopes](https://developers.google.com/people/contacts-api-migration)
- [Microsoft Graph: Get a contact](https://learn.microsoft.com/en-us/graph/api/contact-get?view=graph-rest-1.0)
- [Google Calendar: Inviting attendees](https://developers.google.com/workspace/calendar/api/concepts/inviting-attendees-to-events)
