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

## Независимая проверка требований T047 — 2026-10-27

- [x] T047: русский текст согласия честно описывает read-only доступ к
  контактам аккаунта, ограниченные запросы GRAF, срок видимости и отключение;
  не обещает OAuth-доступ лишь к одному выбранному контакту или удаление у
  провайдера и не смешивает contacts consent с login/calendar/recording.
- [x] T047: отказ/отключение/недоступность источника имеют честное состояние,
  сохраняют ввод email по действующей policy и не создают доступ из подсказки.

Предреализационная проверка T047 пока BLOCK: буквального русского consent
copy для Google/Microsoft ещё нет. FR-024–027, SC-007, plan и contract §8
достаточно определяют ввод email и отделение подсказки от доступа. Все 19
прежних пунктов повторно рассмотрены как требования существующего потока.
Новый интерфейс и полная runtime-матрица доступности не проверялись; старые
ограничения приёмки T048 сохранены. Старый пункт original GRAF clean-room UI
читается по действующей конституции §VII: независимый код и права на материалы
обязательны, визуальное отличие от утверждённого образца не требуется.
Подробный независимый отчёт: `f125-t047-precheck.md` (внешний отчёт).

## Независимая итоговая проверка проекта T047 — 2026-10-27

Первоначальный BLOCK выше снят: contract §8.1 содержит буквальный русский
текст согласия на чтение контактов аккаунта, временную память и честные
пределы отключения. Он не обещает OAuth-доступ к одному выбранному контакту,
не смешивает contacts с login/calendar/recording и не обещает удаление
исходных данных Google/Microsoft. Названы явное подключение/отказ, источник
и понятное состояние недоступности с ручным вводом. Поиск/выбор не равны
выдаче доступа; контракт сохраняет отдельное подтверждённое действие.
Повторно рассмотрены все **21 пункт: 21 checked / 0 unchecked** как качество
требований. Это не проверка работающего интерфейса, VoiceOver, embedded
macOS, provider runtime или выпуска. Исторические пределы T048 сохранены;
действующая Constitution VII определяет независимый код и права на материалы.
Подробный итог и хеши: `f125-t047-precheck.md` (внешний отчёт, итоговое дополнение).

## Независимая проверка решения T046 — 2026-10-27

- [x] T046: сценарий выбора получателя определён без обязательной адресной
  книги — ручной ввод email и разрешённые workspace/calendar подсказки;
  отказ или недоступность источника не создаёт доступ, не блокирует ввод
  и не выдаётся за согласие на запись или подтверждённую identity.

Повторно рассмотрены все 21 прежний пункт качества требований. FR-006–008,
FR-024–028, plan Recipient search authority и quickstart E определяют
сохранённый путь. Отмена native picker не предполагает нового интерфейса;
обещания доступности native source в документах ещё нужно согласовать.
Результат T048 не переносится на установленное приложение, VoiceOver,
provider/native runtime, весь UX или выпуск.
Итог: **22 checked / 0 unchecked**; общий gate пока BLOCK по requirements.
Подробности: `f125-t046-checklist-review.md` (внешний отчёт).


## Независимая итоговая проверка решения T046 — 2026-10-27

Повторно рассмотрены все **22 пункта: 22 checked / 0 unchecked**.
Решение оставляет ручной email и разрешённые workspace/calendar подсказки;
источник не становится подтверждённой identity, согласием или доступом.
Native picker снят с текущего плана, его сценарии применимы только после
нового решения о возвращении; новая поверхность интерфейса не вводится.
Требования доступности, фокуса, понятных состояний и отдельного действия
открытия доступа сохранены. Первоначальный общий BLOCK по requirements снят.
Результаты T048, VoiceOver, embedded macOS и полная пользовательская матрица
не объявлены проверкой native picker или выпуска. Замечаний к требованиям
этого решения нет. Подробности: `f125-t046-checklist-review.md` (внешний отчёт).

## Независимая итоговая проверка проекта T043 — 2026-10-27

Повторно рассмотрены все **22 пункта: 22 checked / 0 unchecked** как
качество требований. US2/US5, scenarios §8.4, Phase 7 и contract §9.1
согласованы: явное принятие может создать personal account до просмотра;
разрешённый summary view подтверждает единственную signup conversion при
отдельном разрешении измерения. CTA, setup и первая собственная запись —
дальнейшие добровольные этапы, без второй регистрации, workspace join или
блокировки разрешённого результата. Existing/self/повтор не дают новую signup.

Новых экранов и источников контактов проект не вводит. Ручной email,
разрешённые подсказки, понятные ошибки, доступность и отдельность выбора и
доступа сохранены. Исторический пункт original GRAF clean-room UI читается
по действующей Constitution VII: независимый код и права на материалы,
без требования визуального отличия от утверждённого образца. Это PASS
проекта T043, без новой проверки браузера, VoiceOver, embedded macOS,
provider/referral runtime или выпуска. Прежняя история сохранена; матрица
каждого пункта и хеши: `f125-t043-final-review.md` (внешний отчёт).

## Независимая проверка требований T042 — 2026-10-27

Повторно сопоставлены все **22 пункта: 22 checked / 0 unchecked** как
качество требований T042/#4448. Девять имён contract §9 сохраняют различие
открытия Share, выбора, grant, запроса/открытия приглашения, разрешённого
просмотра, CTA, единственной signup и отзыва. Выбор не становится доступом,
CTA не блокирует результат, signup не означает вторую регистрацию.
Setup/first own capture остаются отдельными этапами по §9.1, вне узкого каталога.

Новых экранов, текстов или пользовательских действий решение не вводит.
Доступность и browser/embedded договор сохранены; исторический original
clean-room UI читается по Constitution VII как независимый код и права.
Блокирующих пробелов требований нет; браузер, VoiceOver, установленный macOS,
вся воронка и выпуск этим предреализационным ревью не проверялись.
Подробная матрица каждого пункта и контрольные суммы:
`f125-t042-checklist-review.md` (внешний отчёт).

## Независимая итоговая проверка T042 — 2026-10-27

Итоговая T042/#4448 не вводит экранов, пользовательских действий или сбора
событий. Все девять стадий совпадают с исходным contract §9; выбор получателя
не означает grant, CTA не блокирует summary, signup не означает вторую
регистрацию. Неизменённый §9.1 сохраняет явное auth-действие и разрешённый
просмотр, отдельно CTA/setup/first own capture и прежние критерии T044/T045.

Все **22 пункта: 22 checked / 0 unchecked** повторно сопоставлены как
качество требований этого среза, замечаний нет. Независимый профиль каталога
**85 PASS / 0 SKIP**, Ruff PASS; это не новая проверка браузера, VoiceOver,
установленного macOS, provider runtime, всей воронки или выпуска.
Исторические ограничения прежних проверок и Constitution VII сохранены.
Матрица каждого пункта и SHA-256: `f125-t042-final-review.md` (внешний отчёт).
