# Contract: IA, UX, UI and CX

## Navigation model

Keep the existing GRAF shell and sidebar. Add one avatar/account menu: `Профиль`, `Безопасность`, `Уведомления`, `Тариф и оплата`, `Пригласить друзей`, divider, `Выйти`. Destructive account close lives inside Profile. The sidebar subscription card shows server state (`Free`, trial date, `Личный`, `Проверяем продление`) and storage threshold; no hardcoded trial/grace copy.

Account pages are user-scoped. Billing pages show a workspace switcher/header and are workspace-scoped. A user with one personal workspace sees the name but no noisy selector. Owner sees money controls; Admin sees plan/usage; Member sees capability/own usage. Forbidden controls are absent, not disabled with leaked data.

## Screen inventory and controls

| Screen / route | Primary content | Actions and exact labels | Required states |
|---|---|---|---|
| Account overview `/account/profile` | avatar/name, read-only verified email/login identities, locale/timezone/theme, workspace memberships | `Изменить профиль`, `Сохранить`, `Отменить`, `Закрыть аккаунт` | view/edit/dirty/saving/error/saved; email is not implied editable; close eligibility warning |
| Security `/account/security` | login methods, current/other sessions, registered devices | `Добавить способ входа`, `Отключить`, `Завершить сеанс`, `Завершить остальные сеансы`, `Выйти на всех устройствах` | current badge, last activity, cannot-unlink-last-method, re-auth required, revoked |
| Notifications `/account/notifications` | mandatory vs optional channels | `Сохранить настройки` | mandatory locked with explanation, delivery unavailable, dirty/saved |
| Desktop billing summary (embedded) | plan/state, trial/paid-through, unlimited badge, storage used/capacity; no amount/method/history | `Открыть тариф и оплату в браузере`, `Повторить подключение`, `Вернуться к записи` | handoff creating/opening/expired, offline, browser unavailable, renewal-resolution-pending; Record/Stop remains local |
| Billing overview `/account/workspaces/{ws}/billing` | plan/state, payer, trial eligibility/end, paid/bonus-until, next charge/date+amount, unlimited core use, storage/add-on, method, latest invoice | `Начать 7 дней бесплатно` when eligible, `Выбрать тариф`, `Управлять хранением`, `Изменить способ оплаты`, `Отключить автопродление`, `Возобновить Личный` | Free eligible/ineligible for trial, trial without auto-charge, active, cancel scheduled, renewal failed→Free, checking outcome, method required, role lost, provider degraded |
| Usage and storage `/.../billing/usage` | Trial/paid capabilities as `Без лимита` + actual use; Free 18 000-second Moscow-month quota shown as `300 минут`, exact used/remaining as `N мин M сек` without meeting rounding; storage used/reserved/available for 250 MB/500 MB/2 GB or 5/20/100/500 GB total, freshness and `Считаем только meeting-review.m4a` disclosure | `Управлять архивом`, `Удалить данные`, `Обработать без сохранения аудио`, `Добавить хранилище`, `Увеличить хранилище` | normal, Free quota approaching at 80%, Free quota exhausted at 100%, storage 80%, 95%, full, over-capacity after downgrade, stale, storage projection unavailable; color plus icon/text; explicit loss of later audio playback and Free-seconds consequence on no-archive path |
| Plans `/.../billing/plans` | Free 300 min/250 MB, explicit once-only Trial 7 days/500 MB, Личный 2 GB and month/year; `Без лимита по минутам и встречам` immediately paired with finite archive and full-storage alternatives; fair-use review/appeal disclosure | `Начать 7 дней бесплатно`, `Выбрать Личный`, `Настроить хранилище`, `Текущий тариф`, `Связаться с нами` for sales-assisted | monthly/annual, trial eligible/already used/active, current, unavailable, launch config missing; no card for trial and no duplicate paid tier just for GB |
| Checkout summary `/.../billing/checkout` | base/add-on lines, today, discount, next charge/date, unlimited/storage/fair-use, offer/cancel/data copy and email-only external refund boundary; masked receipt contact | promo controls, unchecked offer/recurring consent, `Оплатить {amount} ₽ в YooKassa`, `Назад к тарифам` | stale config/capacity, pro-rata explanation, below-floor, recalculating, invalid promo, operation exists, provider unavailable |
| Payment return `/.../billing/checkout/{operation}` | one operation timeline | `Проверить статус`, `Вернуться в кабинет`, `Добавить способ оплаты` when method_required, `Попробовать снова` only after final canceled | redirect received, processing, success, canceled, unknown, method required; never imply success early |
| Payment method `/.../billing/payment-method` | safe mask/default/status, recurrence explanation | `Добавить способ оплаты`, `Изменить способ оплаты`, `Удалить способ оплаты`, `Отменить` | none, active, binding, failed, revoked/expired; old method stays until verified. Delete is always visible/clickable to billing Owner: with renewal on, guard performs no deletion and offers `Сначала отключить автопродление`; with Free/renewal off, confirmation shows paid-until date and applying/success/failure/concurrent-change |
| Renewal cancel dialog | exact paid-until date and consequences, optional reason | `Отключить автопродление`, `Сохранить подписку` | confirmation, applying, success, concurrent state changed |
| Resume dialog | next date+amount, method | `Возобновить автопродление`, `Изменить способ оплаты`, `Отменить` | method usable/required, applying, success |
| Cycle change dialog | current/new month or year, effective date, no base-plan mid-cycle proration, current/next base+add-on amount, discount fate | `Перейти на год с {date}`, `Перейти на месяц с {date}`, `Отменить` | trial, active next period, cancel scheduled requires resume, renewal unknown blocks, stale catalog |
| Storage capacity dialog `/.../billing/storage` | current/target decimal bytes, used/reserved, 5/20/100/500 GB total-capacity options, measured-hour estimate labelled approximate, paid vs bonus interval, base renewal anchor, exact today/next price | `Добавить хранилище`, `Увеличить до {capacity}`, `Уменьшить с {date}`, `Удалить дополнение с {date}`, `Отменить` | options unavailable until approved price version; initial combined purchase; paid-interval positive pro-rata; bonus-interval change scheduled without charge; pending/success/failure/unknown; downgrade/removal scheduled; target below used warning; concurrent state changed |
| Fair-use review banner/detail | affected capability, bounded reason, effect, exact review deadline, support timeline; no hidden usage balance | `Обжаловать ограничение`, `Скопировать номер для поддержки` | notice pending, restricted, appealed, cleared, confirmed; local Record/Stop and existing data actions remain available |
| History `/.../billing/history` | invoice rows: number, period, amount, payment status, discount and receipt availability; provider refund outcome is not rendered | `Открыть`, `Скачать чек`/`Открыть чек`, `Скопировать номер платежа` | empty/loading/paid/failed/receipt pending; no refund status/filter/badge |
| Invoice detail `/.../billing/invoices/{safe_number}` | immutable price/discount/tax/period/payment and receipt truth plus static external-refund instruction | `Открыть чек`, `Скопировать номер платежа`, `Написать письмо`, `Скопировать email` | no provider id; permission lost; receipt delayed; no refund form/status/result |
| External refund instruction | configured email, safe invoice reference, warning not to send card data/provider ids/meeting links/content, and explicit note that email does not stop future charges | `Написать письмо`, `Скопировать email`, `Скопировать номер платежа`, separate `Отключить автопродление` when applicable | static content and external mail-client failure fallback only; no request/case/status/timeline/SLA/amount/outcome in GRAF |
| Discounts `/.../billing/discounts` | active intro/promo, terms, expiry, historical redemptions | `Добавить промокод`, `Применить`, `Удалить` | empty/valid/invalid/not eligible/exhausted; field label is always visible |
| Referrals `/account/referrals` | personal opaque link, invitee discount, `+7 дней за месяц / +30 дней за год`, 180-day rolling cap, paid/bonus-until, masked status/time-credit ledger | `Скопировать ссылку`, `Поделиться`, `Как это работает`, `Обратиться в поддержку` | no campaign/attributed/pending/available/applied/expired/rejected/reversed; Free credit waiting up to 12 months |
| Referral landing `/r/{opaque}` → signup | inviter benefit without identity disclosure, referee first-period discount, terms/expiry/privacy | `Создать аккаунт`, `Войти`, `Продолжить без бонуса` | valid, expired/invalid, existing account (no re-attribution), already attributed, first-touch stored, conflicting promo later shows best one |
| Account-close preview `/account/close` | subscription stops future charges, memberships/last owner, personal-workspace meeting deletion, sessions, finance retention/retrieval, YooKassa boundary, cooling date | `Назначить другого владельца` when Members exist, `Скачать доступные данные`, `Закрыть аккаунт`, `Отменить закрытие`, `Вернуться` | member workspace blocks until transfer; sole-member personal close enumerates GRAF-controlled deletion, retained finance/backups/YooKassa limits and lifecycle progress; re-auth, cooling, finalizing, canceled, completed, verified-support retrieval |

## Interaction rules

- One primary action per panel/dialog. Explicit verbs replace `Да`, `ОК`, `Продолжить`.
- Monetary submit is disabled only for a stated reason; while pending it retains label and adds progress, without allowing a second operation.
- Recoverable validation preserves safe input. Unknown payment outcome removes any “pay again” CTA until resolved.
- Trial activation has its own confirmation with exact start/end, `Карта не нужна` and `Автосписания не будет`; repeated/concurrent activation explains the once-per-account rule without exposing risk signals.
- `Обработать без сохранения аудио` is present for Free, Trial and `Личный` whenever archival admission is unavailable or explicitly declined; confirmation says no playback audio will remain and, on Free, shows reserved/remaining processing time.
- Trial surfaces show exact `ends_at` with timezone; relative remainder floors days then hours and never rounds up. Free quota uses the distinct 80%/100% copy and does not reuse storage thresholds.
- Destructive/financial confirmations are server-rendered, CSRF-protected and re-check role/state. Browser back/reload is safe and idempotent.
- Base cycle changes apply next period with no hidden proration. Storage capacity upgrades are the sole launch mid-cycle proration: positive difference to shared anchor; downgrade/removal next period. Renewal unknown blocks a new money operation.
- Every billing page places the shared `Нужна помощь с оплатой?` link directly after the main status/action panel. Checkout/provider accessibility failure adds `Не удаётся оплатить из-за доступности? Обратиться в поддержку` in the same location.
- Contextual upgrade prompts are non-coercive and state the exact consequence:
  Free at 80% says `Осталось N мин M сек до сброса {date}` with `Начать 7 дней бесплатно`
  (eligible) or `Выбрать Личный`, plus `Подождать сброса`; Free at 100% keeps
  `Обработать без сохранения аудио` and `Подождать сброса`; Trial T-3/T-1 shows
  the exact end timestamp, `Выбрать Личный` and `Остаться на Free`; expired Trial
  shows `Платный режим закончился` and the same two recovery choices; a blocked
  archival job shows `Увеличить хранилище`, `Удалить старые записи` and
  `Обработать без сохранения аудио`. No prompt hides deletion/export or disables
  local Record/Stop.
- `Написать письмо` opens the external mail client with configured address, subject `Возврат по платежу {safe_invoice_number}` and a short body containing only the safe invoice number plus reminders to describe the request and omit card data, provider ids, meeting links and content. No amount or alleged refund result is prefilled. If no mail client is available, the same block keeps `Скопировать email` and `Скопировать номер платежа` keyboard-accessible. The product does not show a sent/success state.
- Toasts acknowledge noncritical saves; money/cancel/add-on results remain as persistent page status/timeline and live region. The external refund email action has no in-product submission/result confirmation.
- Empty states explain why and give one next action. Errors state separately: money status, access status, pending work and next action.

## Visual system and responsive behavior

Use existing GRAF typography, tokens, cards, buttons and icon style. Competitor content informs hierarchy only; no copied layouts, assets or copy. Dark/light/system theme uses semantic color tokens. Money uses tabular numerals and nonbreaking amount/currency formatting; dates include timezone when consequential.

GRAF account/billing targets WCAG 2.2 AA. At ≤720 px the sidebar collapses into existing menu, tab row becomes a scrollable/stacked select with visible label, summary columns stack, and data tables become labeled rows. At 200% zoom no horizontal page scroll is needed except intentional plan comparison. Minimum target is 24×24 px; critical buttons ≥40 px high. Keyboard focus is visible and not obscured by sticky UI; dialogs trap focus and restore it; help stays in consistent placement; status uses `aria-live`; validation has field association and summary. Verified data is not redundantly re-entered, and re-auth provides an accessible non-cognitive alternative. Reduced motion removes nonessential transitions. Critical navigation/status works without JavaScript; hosted checkout submit may use a normal POST/redirect. YooKassa is an external conformance boundary; GRAF keeps an accessible support/manual recovery route if hosted checkout blocks a user.

## CX copy principles

- Lead with customer consequence: `Продление не подтверждено — сейчас действует Free. Повторно не списываем; проверяем исход платежа`.
- Show exact date/amount before renewal/cancel/resume, and differentiate trial end from auto-charge.
- Never say “карта сохранена у нас”; say “способ оплаты сохранён в YooKassa”.
- Never promise universal deletion, refund eligibility, response SLA or provider settlement; GRAF does not show a refund outcome.
- Unlimited wording names scope: `Без лимита по минутам и встречам`; it never says `Всё без ограничений` or `Безлимитное хранение`.
- The adjacent archive qualifier is mandatory and state-derived: for example, `Включено 2 ГБ для аудиоархива; при заполнении можно продолжить обработку без сохранения аудио или увеличить хранилище`. Free/Trial use their 250/500 MB values; add-on uses its exact total capacity.
- Referral wording says `7/30 дней подписки, не деньги`; status explains maturity/cap/expiry/application/reversal.
- Support reference is safe and copyable. Refund instruction asks for that reference only and warns against card data, provider ids, meeting links/content and screenshots containing them.

## Analytics events

Allowed event classes are coarse: page class, role class, plan code, lifecycle state class, action/result class, anonymous experiment/campaign version. Never capture amount, field values, receipt email, promo code/referral-link token, method data or financial/provider object identifiers. Session replay and Yandex are disabled for the entire account/billing route class.
