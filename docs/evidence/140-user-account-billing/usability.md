# Account/billing usability review (automated and browser interim)

**Дата**: 2026-08-12
**Статус**: automated contract checks pass; moderated human review pending.

Автоматизированно проверяются русские labels, explicit destructive actions,
no-JavaScript POST fallback, `aria-live` status blocks, visible copy about
finite storage/unlimited processing, recoverable promo errors и работа
keyboard-triggered copy controls без передачи значения в analytics.

Manual gate remains: ≥90% discovery of primary actions in 2 minutes, cancel in
≤3 screens/60 seconds, keyboard-only path, 200% reflow, reduced motion and
separate public landing review. Screenshots/video и participant evidence не
хранятся до фактического moderated run.

## Browser evidence 2026-08-12

- focused billing accessibility/UI/usability suite: `39 passed`;
- production Chromium desktop `1200 px`: один `h1`, один `main`, skip-link
  `К содержанию`, named navigation, доступные имена CTA и legal links;
- mobile viewport `390×844`: `scrollWidth == innerWidth`, горизонтального
  overflow нет;
- reduced-motion browser context: media query активна, overflow нет;
- JavaScript-disabled mobile context: landing, download/login CTA, privacy,
  terms и refund/offer navigation остаются server-rendered и доступны;
- browser console: `0 errors`; только два повторяющихся предупреждения о
  заранее загруженных шрифтах без влияния на действие или layout.

Этот проход не измеряет human findability, screen-reader comprehension или
время cancel. Поэтому T079 остаётся открытой до moderated participant evidence.

## Account/settings automated evidence

Проверены browser и embedded маршруты `/account`, `/account/profile`,
`/account/security`, `/account/notifications` и соответствующие `/desktop`
варианты. Account close и notification forms используют обычный `POST` с CSRF,
сохраняют рабочий путь без JavaScript и показывают live-region для результата.
Для login methods зафиксирован recovery-safe guard: последний подтверждённый
способ входа нельзя отключить без другого способа восстановления. Desktop route
policy пропускает account aliases и `/desktop/settings/notifications`.

Evidence: 32 server contract/unit tests plus 22 billing
accessibility/UI/usability checks, 15 macOS `DesktopCabinetRoutePolicyTests`,
plus 2 disposable-PostgreSQL lifecycle tests for server-side preferences and
recovery-safe provider unlink (2026-08-07). Это автоматизированный interim evidence;
ручные проверки keyboard-only, 200% reflow, reduced motion на реальном браузере,
screen reader, clean-room и moderated findability остаются открытыми.
