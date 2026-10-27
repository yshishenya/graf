# UX Requirements Quality Checklist: Обмен встречами

**Purpose**: Validate clarity, accessibility and clean-room requirements before implementation
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## User flow and states

- [x] Share opens only after an explicit owner action
- [x] First surface answers who receives access and what they see
- [x] Search and grant are separate actions with a bounded next step
- [x] Loading, empty, duplicate, blocked, rate-limited and generic failure states are defined
- [x] Current grants, Copy link, revoke, rotation and expiry are discoverable without a role matrix
- [x] External/public unavailable states preserve the typed value and explain the policy
- [x] Recipient onboarding CTA never blocks the permitted summary or creates an account silently

## Accessibility and parity

- [x] Dialog name, modal semantics, combobox/listbox semantics and live status are defined
- [x] Keyboard focus, Escape, overlay close and focus return are defined
- [x] Browser and embedded cabinet share one state/copy contract
- [x] 320 CSS px, 200% zoom, VoiceOver, increased contrast and reduced motion are in acceptance
- [x] Disabled actions cannot trigger requests through stale JavaScript

## Trust and visual quality

- [x] Internal summary-only default and explicit external recording package are understandable in Russian
- [x] Sent/delivered wording does not overpromise mailbox delivery
- [x] Calendar/address-book source and freshness are visible without implying consent
- [x] Email and pre-auth surfaces exclude transcript/audio/summary content; the authenticated recipient page shows only the granted package
- [x] Visual direction remains original GRAF clean-room UI and requires product-design review
- [x] Opening the anonymous invitation link starts automatic personal-account
  bootstrap through the one-time magic-link action; a single visible fallback
  button remains without JavaScript and no sign-up form or password step is
  exposed
- [x] Share confirmation distinguishes invitation creation from mailbox delivery
  and explains that an existing account is reused while a new account receives a
  separate notification

## Notes

All requirement-quality checks pass. A synthetic static browser audit of the
desktop and 320 CSS px modal states was completed on 2026-07-23; the live
browser/embedded acceptance matrix remains a release follow-up and does not
authorize external sharing rollout.

## Независимая проверка требований T048 — 2026-10-27

Повторно проверены все 19 пунктов как качество требований; все подтверждены.
Узкий T048/#4454 сохраняет ввод email при отсутствии адресной книги и
разделяет поиск, локальный выбор получателя и явную отправку. Его браузерная
проверка должна использовать настоящий fragment и `summary-sharing.js`:
ввод адреса и выбор подсказки не запрашивают Contacts permission, не вызывают
нативный мост/провайдера и не отправляют приглашение или grant. Отсутствие
сети/permission нельзя доказывать только поиском строк в JavaScript.

Это не повторная приёмка всей UX-матрицы, VoiceOver, embedded macOS, T042–T047
или общего выпуска. Изменений внешнего вида в тестовом срезе нет; текущая
конституция §VII определяет правила независимой реализации и допустимого
следования утверждённому образцу интерфейса. Ранние визуальные отметки выше
не являются свежим подтверждением работающего интерфейса. Подробный отчёт:
`f125-t048-precheck.md` (внешний отчёт); исполняемые проверки описаны в
[quickstart T048](../quickstart.md#проверка-t048--2026-10-27).

## Независимая итоговая проверка T048 — 2026-10-27

Playwright использует настоящий Jinja fragment и `summary-sharing.js`:
выбор подсказки и ввод неизвестного email дают две видимые локальные строки
без Send. Разрешены только пять ожидаемых GET; Contacts, permissions,
native bridge и ошибки JavaScript наблюдаются отдельными ловушками.
Исполнение включено в оба завершённых профиля 9/9 и 67/67; намеренный Contacts
вызов подтвердил чувствительность отрицательного теста. Замечаний для T048 нет;
19 checked / 0 unchecked. Это браузерная синтетическая проверка изолированного
диалога, а не полная страница, VoiceOver, embedded macOS или приёмка выпуска.
Итоговый отчёт:
`f125-t048-final-review.md` (внешний отчёт); результаты и границы сохранены в
[quickstart T048](../quickstart.md#проверка-t048--2026-10-27).
