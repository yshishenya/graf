# Design QA: Надёжное подключение способов входа

**Дата**: 2026-08-21
**Surface**: server-rendered web cabinet; embedded parity проверяется теми же
templates и отдельными route contracts.
**Browser**: Codex in-app Browser, `http://127.0.0.1:8082`.
**Данные**: только synthetic local account; customer screenshots не создавались.

## Путь и состояние шагов

1. **Вход, wide 1440×900 — здоров.** Доступные и недоступные способы входа
   визуально различимы, email остаётся альтернативным путём, primary action один.
2. **Аккаунт и безопасность, wide — здоров.** Раздел «Способы входа» находится
   в ожидаемой IA, подключённый способ, ограничение на последний recovery method
   и действия email/Яндекс ID/VK ID читаются в одном блоке.
3. **Способы входа, 390×844 — здоров.** Поля и кнопки переносятся без обрезки,
   горизонтальной прокрутки и наложений; OAuth actions следуют сразу после email.
4. **Responsive navigation — здоров.** Единственный rail toggle скрыт до
   готовности JavaScript, имеет state-dependent accessible name и не создаёт
   второй конкурирующий control.
5. **Provider-link outcomes — пройдены по DOM/contracts, без отдельного visual
   verdict.** Success, denied,
   expired, reused, invalid, unavailable и reauth имеют конкретное сообщение,
   один следующий шаг и безопасный выход.
6. **Merge preview/cancel/restart/success — пройдены по DOM/contracts, без
   отдельного visual verdict.** Текст
   называет фактический способ входа; stale proof скрывает старый confirm;
   normal path добавляет только одно осознанное подтверждение.
7. **OTP success и terminal errors — пройдены по DOM/contracts, без отдельного
   visual verdict.** Terminal error
   не оставляет неработающую форму кода; recovery возвращает к новому входу.
8. **Resolved blocker/stale preview — пройдены по DOM/contracts, без отдельного
   visual verdict.** Старый confirm
   скрывается до клика; пользователь сразу получает одну provider-aware кнопку
   нового email/OAuth подтверждения.
9. **Embedded macOS route parity — здоров по route/contracts; визуальный capture
   ограничен.** In-app Browser заблокировал прямую навигацию на
   `/desktop/settings/account` политикой URL. Обход не выполнялся. Embedded
   handlers, тексты, allowlist continuation и narrow/wide contracts покрыты
   автоматическими тестами.

## UX/UI/IA/CX

- Прямое подключение требует одного действия в GRAF до consent провайдера.
- Cross-profile flow добавляет одно отдельное подтверждение после понятного
  результата; cancel не меняет данные.
- Во всех ожидаемых ошибках есть first-party recovery вместо HTTP 500,
  внутреннего exception или повторного заведомо устаревшего confirm.
- Интерфейс использует «профиль», «способ входа» и «пространство»; provider
  subject, nonce, intent ID и RLS не выводятся пользователю.
- Email-originated copy сохраняет «Подключить email»; OAuth-originated copy
  использует «Яндекс ID» или «VK ID».
- Security-hardening browser cookies, exact identity bindings, throttling и
  session revocation не добавляют новых экранов или кликов в normal path.

## Accessibility

- Проверенный DOM содержит один `h1`, логичные section headings, именованные
  regions, labels для полей и доступные имена всех account-linking buttons.
- Результаты и ошибки размечены status/alert semantics; focus styles и
  keyboard-operable native links/buttons/forms сохранены.
- При 390 px controls не обрезаются и сохраняют читаемый порядок.
- Это не visual или assistive-technology evidence для merge, blocker, restart,
  OTP и embedded states и не заявление о полном соответствии WCAG:
  screen-reader announcement, forced-colors, 200% zoom и реальная keyboard-only
  сессия требуют отдельного аппаратного/assistive-technology прохода.

## Screenshot evidence

Снимки сохранены вне git:

`visualizations/2026/08/21/01a023c4-4f39-74b1-921a-49ce99e37eee/feature180-account-linking-audit`

- `01-login-wide-1440.png`
- `08-account-wide-final.png`
- `06-sign-in-methods-mobile-390.png`
- `07-oauth-buttons-mobile-390.png`

Browser console: релевантных warnings/errors не найдено. Wide page overflow:
`scrollWidth == innerWidth`; 390 px capture визуально подтверждает отсутствие
clipped controls и horizontal scroll.
