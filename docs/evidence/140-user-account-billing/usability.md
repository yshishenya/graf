# Account/billing usability review (automated interim)

**Дата**: 2026-08-07
**Статус**: automated contract checks pass; moderated human review pending.

Автоматизированно проверяются русские labels, explicit destructive actions,
no-JavaScript POST fallback, `aria-live` status blocks, visible copy about
finite storage/unlimited processing и отсутствие refund form/status in product.

Manual gate remains: ≥90% discovery of primary actions in 2 minutes, cancel in
≤3 screens/60 seconds, keyboard-only path, 200% reflow, reduced motion and
separate public landing review. Screenshots/video и participant evidence не
хранятся до фактического moderated run.

## Account/settings automated evidence

Проверены browser и embedded маршруты `/account`, `/account/profile`,
`/account/security`, `/account/notifications` и соответствующие `/desktop`
варианты. Account close и notification forms используют обычный `POST` с CSRF,
сохраняют рабочий путь без JavaScript и показывают live-region для результата.
Для login methods зафиксирован recovery-safe guard: последний подтверждённый
способ входа нельзя отключить без другого способа восстановления. Desktop route
policy пропускает account aliases и `/desktop/settings/notifications`.

Evidence: 32 server contract/unit tests, 15 macOS `DesktopCabinetRoutePolicyTests`,
plus 2 disposable-PostgreSQL lifecycle tests for server-side preferences and
recovery-safe provider unlink (2026-08-07). Это автоматизированный interim evidence;
ручные проверки keyboard-only, 200% reflow, reduced motion на реальном браузере,
screen reader, clean-room и moderated findability остаются открытыми.
