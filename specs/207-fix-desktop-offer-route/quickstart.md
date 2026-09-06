# Quickstart: Safe Desktop Offer Route

## Prerequisites

- Запускать из корня чистого feature worktree.
- Не запускать реальный или тестовый платёж для этой проверки.
- Production smoke выполнять только на штатном signed, notarized и stapled macOS release.

## Focused validation

```sh
swift test --package-path apps/macos --filter DesktopCabinetBillingHandoffTests
swift build --package-path apps/macos
```

Expected:

- `/offer` получает external decision.
- Sanitized URL равен `https://<configured-origin>/offer` и не содержит query/fragment.
- `/offer/`, `//offer`, `/offer//`, `/offer/extra` и HTTP-вариант остаются blocked.
- Existing billing routes and payment-provider allowlist tests pass.

## Repository gate before PR

```sh
infra/scripts/ci-local.sh --fast
```

Expected: server unit suite, lint and compile gates pass. Full CI is deferred to the approved release candidate.

## Production installed-app smoke after release

1. Открыть `/Applications/GRAF.app` и перейти: `Аккаунт и безопасность → Тариф и оплата → Выбрать тариф`.
2. Записать исходные billing history, статус подписки и значение checkbox согласия.
3. Нажать ссылку `оферту`.
4. Подтвердить, что default browser открыл `https://rec.2brain.pro/offer` без query и fragment.
5. Вернуться в GRAF и подтвердить, что checkout доступен и не показывает `Функция недоступна`.
6. Сравнить с baseline: billing history, статус подписки и checkbox согласия не изменились.

Release proof дополнительно включает exact SHA, full CI, Developer ID, notarization, stapling, Gatekeeper, Sparkle feed/archive verification и установленную версию.
