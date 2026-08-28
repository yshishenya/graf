# Quickstart: Safe Desktop Offer Route

## Prerequisites

- Запускать из корня чистого feature worktree.
- Не запускать реальный или тестовый платёж для этой проверки.
- Production smoke выполнять только после штатного signed macOS release.

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
2. Нажать ссылку `оферту`.
3. Подтвердить, что default browser открыл `https://rec.2brain.pro/offer` без query и fragment.
4. Вернуться в GRAF и подтвердить, что checkout доступен и не показывает `Функция недоступна`.
5. Проверить, что billing history и статус подписки не изменились, а checkbox
   согласия сохранил прежнее значение.

Release proof дополнительно включает exact SHA, full CI, Developer ID, notarization, stapling, Gatekeeper, Sparkle feed/archive verification и установленную версию.
