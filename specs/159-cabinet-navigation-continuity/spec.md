# Feature Specification: Непрерывная навигация кабинета

**Feature Branch**: `codex/159-cabinet-navigation-continuity`

**Created**: 2026-08-17

**Status**: Implementation committed and validated locally; PR pending

**Input**: Продолжение общего owner journey GRAF: единая боковая навигация,
поиск, профиль, настройки, скачивание приложения и truthful auth surface в web
и embedded macOS shell.

## User Scenarios & Testing

### User Story 1 - Понятный и стабильный кабинет (Priority: P1)

Пользователь открывает список встреч или встречу и сразу понимает, как
свернуть боковую панель, найти встречу, открыть настройки или профиль. Эти
действия должны выглядеть и работать одинаково в браузере и embedded-версии.

**Why this priority**: Общий shell используется на каждой защищённой странице;
ошибка здесь блокирует навигацию, поиск и восстановление контекста.

**Independent Test**: В synthetic browser/embedded render matrix открыть список
встреч в expanded и collapsed состояниях, выполнить два последовательных
переключения, проверить поиск с русской строкой, web-only download CTA и
профильное меню без реальных встреч или пользовательских данных.

**Acceptance Scenarios**:

1. **Given** боковая панель раскрыта, **When** пользователь активирует один
   toggle мышью, Enter или Space, **Then** панель скрывается, toggle остаётся
   в том же hit target и следующий action label сообщает «Показать боковую
   панель».
2. **Given** панель скрыта, **When** пользователь повторно активирует тот же
   toggle без перемещения указателя, **Then** панель раскрывается, focus не
   теряется, active route не меняется, а toggle сообщает «Скрыть боковую
   панель».
3. **Given** поле поиска находится в обычном, focus, loading, disabled или
   typed-состоянии, **When** отображается иконка и русский запрос, **Then** у
   иконки и текста есть отдельное пространство без перекрытия, клики по иконке
   доходят до поля, а узкая ширина не создаёт горизонтальный overflow.
4. **Given** пользователь находится в обычном web shell, **When** он ищет
   загрузку приложения, **Then** на странице есть ровно одна доступная ссылка
   на канонический `/download`; **When** shell embedded, **Then** sidebar CTA
   скачивания отсутствует и остаётся native-owned update affordance.
5. **Given** доступны имя и подтверждённый email пользователя, **When** он
   открывает профильное меню, **Then** меню показывает только безопасные
   профильные данные, «Настройки» и «Выйти», закрывается по Escape или клику
   снаружи и возвращает focus на кнопку профиля.

### User Story 2 - Одна ясная навигация в настройках (Priority: P1)

Пользователь открывает настройки из кабинета, видит одну основную левую
навигационную область с существующими разделами и может вернуться к встречам
одним очевидным действием.

**Why this priority**: Две конкурирующие левые панели создают ложную иерархию
и затрудняют доступ к server-backed forms.

**Independent Test**: Открыть каждую существующую settings category и calendar
surface в web и embedded, проверить одну видимую accessible rail, selected
state, canonical «К встречам» и отсутствие горизонтального overflow на узком
viewport.

**Acceptance Scenarios**:

1. **Given** пользователь открыл любой существующий раздел настроек, **When**
   страница отображается, **Then** видна ровно одна основная settings rail,
   текущая категория имеет `aria-current`, а все существующие destinations
   остаются достижимыми.
2. **Given** пользователь находится в настройках, **When** он выбирает «К
   встречам», **Then** переход ведёт на канонический главный экран текущей
   поверхности и не требует случайного browser history.
3. **Given** viewport узкий, **When** пользователь открывает settings rail,
   **Then** navigation не занимает весь первый экран, labels остаются читаемыми,
   а horizontal overflow отсутствует.

### User Story 3 - Правдивый вход и surface parity (Priority: P1)

Пользователь видит на login surface правдивое объяснение email-входа и не
получает ложного обещания автоматической регистрации. При этом явный signup,
invitation, provider, email-code, session recovery и legacy `/sign-up` paths
остаются безопасно достижимыми.

**Why this priority**: Auth UI является частью trust boundary; визуальное
упрощение не должно менять создание аккаунта, CSRF, tenant, rate-limit или
session semantics.

**Independent Test**: Пройти synthetic contract matrix для unknown email,
existing user, explicit signup, invitation/provider, email-code, expired session
и прямого `/sign-up` в браузере и embedded surface без реальных credentials.

**Acceptance Scenarios**:

1. **Given** неизвестный email отправлен через обычный login, **When** сервер
   обрабатывает flow, **Then** аккаунт молча не создаётся, а пользователь
   получает truthful login/recovery outcome.
2. **Given** пользователь открывает `/sign-up` или invitation/provider flow,
   **When** он продолжает регистрацию или вход, **Then** исходный explicit
   route остаётся достижимым и не ослабляет CSRF, callback, exact-email,
   account-linking, session, rate-limit или tenant boundaries.
3. **Given** одинаковый flow открыт в web и embedded, **When** меняется только
   surface, **Then** auth outcome, localized reason и allowed return path имеют
   одинаковый смысл.

### Edge Cases

- Профиль без имени, с длинным именем или непрерывным длинным email не должен
  расширять sidebar, обрезаться многоточием или создавать overflow.
- Повторные HTMX/partial updates не должны добавлять несколько toggle,
  profile-menu или outside/Escape handlers.
- Toggle должен корректно отображаться в collapsed state, а focus должен
  оставаться управляемым при повторной активации.
- Если публичная загрузка временно недоступна, web shell не должен обещать
  несуществующий файл; embedded shell не должен показывать download CTA.
- Settings category, calendar path или account alias, недоступный конкретной
  роли, должен сохранить существующую безопасную ошибку/redirect, а не получить
  новый обход authorization.
- Expired session, CSRF error и blocked external auth continuation должны
  оставаться отдельными состояниями, а не маскироваться UI-изменением.
- Reduced-motion, dark/light, keyboard-only и узкий viewport не должны менять
  семантику доступных действий.

## Requirements

### Functional Requirements

- **FR-001**: Кабинет MUST иметь один общий sidebar toggle в стабильном месте
  expanded и collapsed states; его visible label, tooltip/title,
  `aria-expanded`, `aria-controls` и icon MUST описывать следующее действие.
- **FR-002**: Toggle MUST принимать pointer, Enter и Space activation, сохранять
  focus и active navigation, а повторная активация без движения указателя MUST
  возвращать предыдущее состояние.
- **FR-003**: Search field MUST резервировать отдельное пространство для icon,
  placeholder, typed text и optional clear action во всех desktop, embedded,
  narrow, focus, loading и disabled states.
- **FR-004**: Обычный web shell MUST показывать ровно один keyboard-focusable
  CTA на `/download` в логичном месте sidebar; embedded shell MUST показывать
  ноль sidebar download CTA и MUST сохранять native-owned updater action.
- **FR-005**: Sidebar MUST показывать текущего пользователя в нижней части без
  увеличения своей ширины; safe display name и verified email MAY переноситься,
  но provider subject, internal IDs, tokens и иные sensitive fields MUST быть
  исключены.
- **FR-006**: Profile menu MUST содержать только safe profile information,
  «Настройки» и существующий безопасный logout action; оно MUST закрываться по
  Escape/outside click, не быть настоящей modal focus trap и возвращать focus.
- **FR-007**: Browser и embedded shell MUST использовать один shared interaction
  contract для toggle, search, download visibility, profile menu и active route.
- **FR-008**: Settings surface MUST иметь ровно одну видимую и доступную основную
  navigation rail, canonical return to meetings и unambiguous selected category.
- **FR-009**: Settings MUST reuse existing category links, destinations, forms,
  CSRF, role, billing, auth and native recording handoff semantics; новый
  settings source, SPA router или localStorage state MUST NOT be introduced.
- **FR-010**: All existing settings categories, calendar paths, account aliases
  and embedded/browser destinations MUST remain reachable or preserve their
  existing authorized blocked state.
- **FR-011**: Login UI MUST be truthful that normal unknown-email login does not
  create an account; explicit signup, invitation, provider and email-code flows
  MUST remain reachable where currently supported.
- **FR-012**: This slice MUST NOT change CSRF, OAuth callback state/nonce,
  exact-email, account-linking, session, rate-limit, tenant, role, billing or
  logout semantics.
- **FR-013**: Web and embedded auth surfaces MUST preserve equivalent outcome
  meaning, localized copy and safe return paths; embedded external-navigation
  boundary MUST remain intact.
- **FR-014**: All new or changed controls MUST expose keyboard operation, visible
  focus, accessible name/state and Russian copy; behavior MUST remain usable with
  reduced motion and in both supported color schemes.
- **FR-015**: Partial updates and repeated initialization MUST be idempotent for
  shared event handlers and MUST NOT duplicate controls, landmarks or download
  CTAs.
- **FR-016**: Evidence MUST use synthetic fixtures or metadata-only facts; real
  credentials, meetings, transcripts, audio, provider subjects, tokens and
  private screenshots MUST NOT enter the repository or validation artifacts.

### Out of Scope

- Native macOS WKWebView Back/Forward/Reload/Home controls; those belong to the
  successor native-shell slice (Feature 160).
- New settings categories, settings persistence, SPA routing, account or profile
  storage, new download endpoints, UA sniffing and updater implementation.
- Changing auth account-creation, account-linking, provider callback, CSRF,
  billing, role, tenant, recording-policy or logout backend semantics.
- Replacing the existing settings category/form owners from Features 135 and 151.
- New analytics, onboarding systems or competitor-specific visual copying.

### Key Entities

- **Cabinet shell surface**: Shared browser or embedded presentation mode with
  the same navigation/action contract and an explicit `embedded` boundary.
- **Cabinet navigation item**: Existing safe route item with id, label, icon,
  active state and surface-specific href.
- **Safe profile projection**: Existing account profile presentation containing
  display name and verified email only; it is not an identity/token model.
- **Settings category view**: Existing server-owned settings destination with
  category id, label, scope, href, group and selected state.
- **Auth entry intent**: Existing login/signup/invitation/provider/email-code
  path plus safe return target; no new auth state is introduced here.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Synthetic browser and embedded shell matrix finds exactly one
  toggle contract, one shared action label per state, and zero duplicate toggle
  or handler markers after repeated partial initialization.
- **SC-002**: Search contract passes 100% of desktop, embedded, narrow, Russian
  typed, loading, disabled and focus states with a non-zero icon/text gap and no
  horizontal overflow.
- **SC-003**: Ordinary web render contains exactly one focusable `/download`
  sidebar CTA and embedded render contains zero sidebar download CTAs across
  meeting list, meeting detail and settings surfaces.
- **SC-004**: Profile contract passes short/long/missing-name and long-email
  synthetic cases with no sensitive-field markers, no overflow, Escape/outside
  close and focus return.
- **SC-005**: Every existing settings category and calendar surface passes
  browser/embedded route checks with exactly one settings navigation landmark,
  one selected state and a working canonical return to meetings.
- **SC-006**: Auth contract matrix records no change in unknown-email, signup,
  invitation/provider, email-code, expired-session, CSRF or return-path outcomes.
- **SC-007**: All focused tests, `node --check` and `infra/scripts/ci-local.sh
  --fast` pass on one exact SHA; any unavailable visual/browser environment is
  recorded as a concrete limitation rather than implied success.
- **SC-008**: No validation artifact contains real credentials, meeting content,
  audio, transcript text, provider subject, token, signed URL or private
  screenshot.

## Assumptions

- Existing shared server-rendered cabinet templates, CSS, JavaScript and view
  models are the source of truth for browser and embedded shell parity.
- Features 135 and 151 remain owners of settings categories and forms; this
  slice changes their shell placement/visibility only.
- Current auth audit is authoritative: normal unknown-email login is rejected,
  while explicit signup/invitation/provider/email-code flows remain supported.
- `/download` is the canonical public download destination, and embedded update
  action is already native-owned.
- No production deploy, public release, native macOS shell change or real-user
  visual evidence is required for this slice.
