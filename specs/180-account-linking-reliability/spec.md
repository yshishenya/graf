# Feature Specification: Надёжное подключение способов входа

**Feature Branch**: `180-account-linking-reliability`

**Created**: 2026-08-21

**Status**: Ready for implementation

**Input**: User description: "Исправить весь путь подключения и объединения учётных записей: production 500, все функции и endpoints, каждую кнопку и строку, UX/UI/IA/CX, стопперы и тупики; минимизировать число действий пользователя."

### Clarifications

#### Session 2026-08-23

- Q: Как должна выглядеть модель пространств после объединения профилей? → A: У пользователя одно личное пространство; корпоративные пространства сохраняются только как доступ по приглашению или membership.
- Q: Как объединять личные встречи и их артефакты? → A: Простое объединение без дедупликации: 4 встречи и 10 встреч становятся 14 видимыми встречами; аудио, транскрипты и саммари остаются у своих встреч.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Подключить способ входа без ошибки сервера (Priority: P0)

Уже вошедший пользователь открывает настройки профиля и подключает доступный
способ входа. Начало OAuth-перехода, callback и подтверждение работают в web и
встроенном macOS-кабинете без ошибки сервера и без ослабления разграничения
данных.

**Why this priority**: Производственный путь сейчас обрывается до перехода к
провайдеру, поэтому пользователь не может достичь основной цели.

**Independent Test**: Для каждого доступного OAuth-провайдера начать
подключение из web и embedded settings с production-equivalent политиками
доступа; получить безопасный redirect, пройти callback и прямое подключение.

**Acceptance Scenarios**:

1. **Given** активная подтверждённая сессия и доступный провайдер, **When** пользователь нажимает «Подключить», **Then** GRAF создаёт одноразовое состояние в разрешённом auth-контексте и перенаправляет к провайдеру без HTTP 500.
2. **Given** корректный callback того же браузера, **When** внешний аккаунт ещё не принадлежит другому профилю, **Then** способ входа подключается к текущему профилю и настройки показывают понятный успех.
3. **Given** отсутствующий, неверный, просроченный или повторно использованный callback proof, **When** callback или confirm отправлен, **Then** операция fail-closed, данные не меняются и пользователь получает конкретное действие для нового запуска.
4. **Given** API-клиент с активной customer membership, **When** он начинает тот же provider-link flow, **Then** API использует тот же разрешённый auth-контекст и не зависит от обхода RLS.

---

### User Story 2 - Безопасно объединить два профиля (Priority: P0)

Если подтверждённый способ входа уже принадлежит другому профилю, GRAF
показывает один адаптивный экран решения. Экран называет реальный способ входа,
объясняет результат, сохраняет пространства и даёт подтвердить или оставить
профили раздельными без скрытых изменений.

**Why this priority**: Cross-profile callback является ожидаемым продолжением
подключения, а не ошибкой; неверная email-терминология снижает доверие и
создаёт ошибочное согласие.

**Independent Test**: Создать provider-link-originated merge intent для каждого
поддерживаемого провайдера и email-link-originated intent; проверить preview,
confirm, cancel, success и повторный вход.

**Acceptance Scenarios**:

1. **Given** способ входа принадлежит другому профилю, **When** открывается preview, **Then** заголовок, пояснение и основное действие называют этот способ входа, а не всегда email.
2. **Given** свежие точные proofs и отсутствие blockers, **When** пользователь подтверждает, **Then** текущий профиль остаётся основным, способы входа и личные данные атомарно переходят в одно личное пространство, корпоративные memberships сохраняются, а пользователь получает один понятный путь повторного входа.
3. **Given** пользователь выбирает оставить профили раздельными, **When** отмена завершается, **Then** ни профиль, ни данные не меняются, intent безопасно завершается и настройки показывают результат.
4. **Given** у любой стороны нет ровно одного личного пространства с активным owner-доступом либо есть отдельно принадлежащее ей corporate/неизвестное пространство, **When** строится preview, **Then** объединение блокируется до любых изменений данных.
5. **Given** в личных профилях 4 и 10 встреч, **When** merge завершается, **Then** в одном личном пространстве видны все 14 встреч; записи не дедуплицируются и связанные аудио, транскрипты и саммари не теряются.

---

### User Story 3 - Восстановиться после устаревшего подтверждения (Priority: P0)

Если сессия, callback или подтверждённый способ входа больше не совпадает с
intent, пользователь не попадает в цикл повторного нажатия неработающей кнопки.
GRAF объясняет, что старое подтверждение больше не действует, и запускает
новое подтверждение из безопасной точки.

**Why this priority**: Повтор прежнего confirm не может исправить stale proof и
образует тупик в security-critical сценарии.

**Independent Test**: Для каждого proof mismatch открыть preview, нажать
доступное recovery-действие и получить новый flow без повторного использования
старого intent.

**Acceptance Scenarios**:

1. **Given** confirm вернул `proof_required`, **When** страница результата открыта, **Then** старое primary confirm недоступно, причина изложена простым языком и есть действие «Начать заново».
2. **Given** пользователь начинает заново, **When** исходный способ входа известен и доступен, **Then** GRAF ведёт прямо к соответствующему provider/email start без лишнего промежуточного экрана.
3. **Given** автоматический restart небезопасен или провайдер недоступен, **When** пользователь открывает состояние, **Then** GRAF возвращает к способам входа с ясным сообщением и не обещает выполненное подключение.

---

### User Story 4 - Понять и пройти путь на любом поддерживаемом экране (Priority: P1)

Путь в web и macOS использует одну информационную архитектуру, короткие
понятные формулировки и доступные действия. На каждом состоянии виден следующий
шаг; отсутствуют внутренние термины, лишние подтверждения и горизонтальная
прокрутка.

**Why this priority**: Технически корректный auth flow остаётся непригодным,
если пользователь не понимает последствия или не может найти следующий шаг.

**Independent Test**: Пройти state/action matrix клавиатурой на wide и 390 px,
проверить heading/focus/status semantics и desktop route allowlist.

**Acceptance Scenarios**:

1. **Given** настройки способов входа, **When** пользователь просматривает доступные варианты, **Then** каждый вариант имеет уникальную понятную подпись, состояние и одно основное действие.
2. **Given** любой успех, отказ, expiry, blocker или unavailable state, **When** он отображён, **Then** есть конкретный безопасный следующий шаг и нет внутренних слов вроде preview, intent, survivor, provider subject или RLS.
3. **Given** ширина 390 px, увеличение масштаба или клавиатурная навигация, **When** пользователь проходит путь, **Then** действия доступны, порядок чтения логичен, фокус виден, результаты объявляются и горизонтальной прокрутки нет.
4. **Given** embedded macOS surface запускает внешний OAuth, **When** переход покидает first-party кабинет, **Then** используется существующее external-auth continuation без расширения неизвестных разрешённых маршрутов.

### Edge Cases

- Провайдер выключен, неверно настроен или становится недоступным между start и callback.
- Start повторяется двойным кликом или параллельно из двух вкладок.
- Callback приходит без browser-state cookie, с чужим state, после expiry или после успешного consume.
- Внешняя identity уже связана с текущим профилем, другим профилем либо несколькими повреждёнными записями.
- Инициирующая сессия отозвана, заменена или принадлежит способу входа, отличному от ожидаемого proof.
- Preview устарел из-за изменения billing, calendar, deletion, membership, workspace или identity состояния.
- Confirm и cancel отправляются одновременно или повторяются с тем же/другим idempotency key.
- У одной из сторон нет ровно одного personal workspace либо нет его активного owner membership; объединение блокируется без изменений.
- У провайдера нет user-facing названия; интерфейс использует безопасную нейтральную подпись без технического ID.
- Support не настроен; интерфейс не заявляет о создании обращения и оставляет путь назад.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Все web и API provider-link start endpoints MUST создавать callback state только после применения минимально необходимого auth-контекста, разрешённого политиками доступа.
- **FR-002**: Исправление MUST сохранять RLS fail-closed; запрещено расширять policy до обычного request-контекста или отключать tenant checks ради provider linking.
- **FR-003**: Web, embedded и API paths MUST использовать один и тот же security contract для state, nonce, session, identity и callback proof.
- **FR-004**: Каждый start, callback, confirm, cancel и restart MUST иметь явные outcomes для success, invalid, denied, expired, reused, conflict, unavailable и proof mismatch; непредвиденная ошибка не должна превращать ожидаемое состояние в HTTP 500.
- **FR-005**: Cross-profile provider linking MUST создавать bounded merge preview для любого допустимого initiating sign-in provider, если security proofs достаточны; поведение не должно искусственно зависеть от email-сессии.
- **FR-006**: Merge page MUST выводить user-facing имя фактического подключаемого способа входа в title, subtitle, primary action, result и relogin copy.
- **FR-007**: Email-originated flow MUST сохранить привычную формулировку «Подключить email»; OAuth-originated flow MUST использовать соответствующее название провайдера; неизвестный provider MUST использовать «Подключить способ входа».
- **FR-008**: `proof_required` и другие stale-proof состояния MUST отключать повтор старого confirm и предлагать новый bounded start либо возврат к способам входа.
- **FR-009**: Restart MUST создать новые callback state, nonce и proof; существующий незавершённый merge intent MAY быть безопасно перепривязан к этим exact fresh bindings до показа нового preview.
- **FR-010**: Confirm MUST повторно проверять exact initiating session, source identity, callback proof и provider-link state непосредственно перед mutation.
- **FR-011**: Подтверждение MUST быть одноразовым, идемпотентным и атомарным; ошибки и конкуренция MUST не оставлять частичный перенос identity, memberships, workspace, sessions или audit state.
- **FR-012**: После успешного merge текущий профиль MUST остаться основным, а все доступные подтверждённые способы входа MUST сохраниться без дублей.
- **FR-013**: Каждая сторона MUST иметь ровно один personal workspace с активным owner membership; после merge личные workspace-scoped данные source MUST атомарно перейти в survivor personal workspace, все личные встречи MUST стать видимыми в survivor без дедупликации, а source personal workspace MUST быть удалён или выведен из пользовательской области без потери данных. Отдельно принадлежащие corporate/неизвестные ownership shapes MUST блокировать merge до mutation.
- **FR-014**: Billing, calendar, deletion, ownership, active-operation и другие blocker checks Feature 178 MUST остаться fail-closed и показывать реальное доступное действие.
- **FR-015**: Cancel MUST сохранять оба профиля и данные без изменений, безопасно завершать intent и возвращать в настройки с понятным результатом.
- **FR-016**: Success MUST отзывать затронутые сессии/device trust и вести пользователя к одному повторному входу с ясным объяснением.
- **FR-017**: Settings MUST использовать слова «профиль», «способ входа» и «пространство» и MUST не показывать внутренние слова preview, merge intent, survivor, ownership conflict, provider subject или RLS; после merge MUST показывать одно личное пространство и корпоративные пространства, доступные через membership.
- **FR-018**: Каждый экран и состояние MUST иметь не более одного primary action, безопасный secondary exit и конкретный recovery action там, где повтор возможен.
- **FR-019**: Нормальный путь start → provider → callback → direct link MUST требовать одно пользовательское действие в GRAF до внешнего consent; merge path MUST добавлять только одно осознанное подтверждение.
- **FR-020**: Повторный вход после успешного merge MUST быть доступен напрямую с result page без возврата вручную через настройки.
- **FR-021**: Все действия MUST быть keyboard-operable, иметь видимый focus, доступные имена, логичный heading order и объявляемый status/error; narrow layout MUST не иметь горизонтального overflow.
- **FR-022**: Web и macOS MUST сохранять одинаковые тексты, состояния и outcomes, используя существующий server-rendered UI и существующий allowlist external-auth continuation.
- **FR-023**: Audit, логи, тестовые evidence и diagnostics MUST оставаться metadata-only и не содержать реальных email, токенов, кодов, raw identifiers, содержимого встреч или customer screenshots.
- **FR-024**: Production-equivalent regression MUST выполнять provider-link start и callback под реальной ролью приложения с включёнными RLS policies, а не только через mocked/in-memory context.
- **FR-025**: Regression matrix MUST покрывать email и каждый поддерживаемый OAuth provider, web/API/embedded entry points, direct link, merge, cancel, restart, expiry, replay, concurrency и blocker outcomes.
- **FR-026**: Existing login, email linking, provider linking, session/device, workspace access и account-close regression MUST оставаться зелёными.
- **FR-027**: Browser authentication completion MUST быть связано с
  unpredictable proof того браузера, который начал email/OAuth flow; relayed
  proof не должен устанавливать browser session.
- **FR-028**: Короткий email code MUST храниться только как purpose-separated
  server-keyed digest, который нельзя перебрать offline по snapshot базы без
  server secret и browser proof.
- **FR-029**: Отключение способа входа MUST в той же транзакции отзывать
  активные sessions/device bindings, выданные через этот provider, включая
  текущую сессию с прямым relogin recovery.
- **FR-030**: Public OAuth start/callback MUST иметь application-level rate
  limits до роста state/provider I/O, а синхронный provider client MUST не
  блокировать async request loop.

### Key Entities

- **Provider-link state**: Одноразовый запрос текущего пользователя на подключение конкретного способа входа, связанный с инициирующей сессией и callback proof.
- **Callback state/proof**: Короткоживущее подтверждение внешнего auth-перехода и того же браузера; создаётся и читается только в разрешённом auth-контексте.
- **Account-linking intent**: Одноразовое решение между двумя подтверждёнными профилями с fingerprint preview, blockers и exact proof bindings.
- **Provider presentation**: Безопасное user-facing имя и действия для фактического источника intent без раскрытия provider subject или raw identifiers.
- **Workspace root**: Единственное personal пространство пользователя и отдельные corporate пространства, доступные через membership; внутренний linked root не является пользовательским пространством.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% production-equivalent provider-link start tests для web и API возвращают ожидаемый redirect/response; ноль HTTP 500 и ноль RLS violations.
- **SC-002**: 100% direct-link и merge tests для поддерживаемых providers завершаются ожидаемым outcome без потери identity, workspace, meeting или membership access.
- **SC-003**: 100% invalid, expired, reused, mismatched и concurrent proof cases fail-closed, не меняют account data и показывают безопасный следующий шаг.
- **SC-004**: 100% merge screens и result copy называют фактический способ входа; email-only текст не появляется в OAuth-originated flow.
- **SC-005**: Ни одно протестированное состояние не оставляет пользователя с повтором заведомо неработающего confirm, только сообщением об ошибке или отсутствующим выходом.
- **SC-006**: Direct-link path требует одного клика в GRAF до внешнего consent; merge path требует ровно одного дополнительного осознанного подтверждения.
- **SC-007**: Wide и 390 px runtime checks находят ноль clipped controls, горизонтального page overflow и недоступных keyboard actions.
- **SC-008**: Полный focused server test matrix, lint и repository validation gate проходят без новых failures; существующие auth/account-linking regressions остаются зелёными.
- **SC-009**: Независимые backend/security, code и product-design reviews не содержат незакрытых P0/P1/P2 findings перед handoff.
- **SC-010**: Regression доказывает, что relayed email/API OAuth proof без
  initiating-browser binding не создаёт browser session.
- **SC-011**: Отключённый provider немедленно теряет все выданные им sessions,
  другие providers и recovery path сохраняются.
- **SC-012**: Rate-limited OAuth start/callback не создаёт state и не вызывает
  provider adapter; provider verification выполняется вне event loop.

## Assumptions

- Feature 178 остаётся базовым продуктовым и security-контрактом; этот slice исправляет его runtime и UX gaps, не ослабляя blockers.
- Используется существующий server-rendered кабинет и существующие модели; новый wizard, SPA state, provider SDK или dependency не требуется.
- Поддерживаемые provider IDs и их user-facing labels берутся из текущей конфигурации GRAF; недоступные провайдеры не рекламируются как рабочие.
- Реальный production deploy, release, миграция пользовательских данных и commit выполняются только после отдельного release/commit approval.

## Out of Scope

- Добавление нового внешнего OAuth-провайдера или изменение его consent screen.
- Перенос активных billing/calendar credentials между пространствами; такие состояния остаются blockers. Сведение личных workspace-scoped данных в единственное personal пространство входит в задачу.
- Ручное исправление конкретной production-записи пользователя до проверки исправления и отдельного operational approval.
- Ослабление RLS, proof binding, nonce, idempotency, blocker или session-revocation требований.
