# Production closeout: `v2026.08.28.11`

Дата: 2026-08-28  
Контур: `2brain.dev` / `https://rec.2brain.pro`

Receipt содержит только технические метаданные. Секреты, signed URLs, аудио,
расшифровки и содержимое встреч не включались.

## Immutable release

- Tag и GitHub Release: [`v2026.08.28.11`](https://github.com/yshishenya/graf/releases/tag/v2026.08.28.11).
- Release, production runtime и public appcast SHA:
  `c428f7990843cc39c141b25c3d8dfdc8de3d66f2`.
- Release title: `v2026.08.28.11 — биллинг в приложении и устойчивый deploy`.
- Validation lane: release/deploy, high-risk billing navigation и production
  healthcheck.

## Exact-SHA validation и production deploy

| Гейт | Результат |
| --- | --- |
| Full macOS suite | PASS, `768/768` |
| Full server suite | PASS, `3487 passed, 1 skipped` |
| Performance contract | PASS, `1 passed` |
| Strict PostgreSQL/RLS | PASS, `52 passed, 1 skipped` |
| Lint, compile, Compose, evidence scan | PASS |
| CD dry-run и approved execute | PASS на exact SHA |
| Backup и restore rehearsal | PASS; backup `/opt/projects/2brain-rec/backups/20260828T154339Z` |
| Migrations, production smoke и cleanup | PASS |
| Public health | `/api/v1/health/live=200`, `/api/v1/health/ready=200` |
| API container | `healthy` |
| Rollback | Не потребовался |

После deploy выполнен metadata-only runtime readback: checkout `true`, emergency
stop `false`, YooKassa environment `test`, shop suffix `6758`. Production-магазин
не включался.

## Public macOS release

- Universal `arm64 + x86_64`, Developer ID Application/Installer: PASS.
- Apple notarization `Accepted`: ZIP request
  `6f6fb6fd-e3f0-4597-b499-e8fcf885526d`; PKG request
  `15fee937-4c67-49d8-b94f-80807ed5bb32`.
- Stapler, codesign, package signature и `spctl`: PASS. Проверяющий Mac сообщил
  системный `security disabled` override, но assessment вернул `accepted` с
  источником `Notarized Developer ID`.
- Sparkle local Keychain signer: custody `ready`, trust generation `1`;
  Developer ID -> Developer ID continuity `2026.08.28.8 -> 2026.08.28.11` —
  PASS.
- Public ZIP: `GRAF-2026.08.28.11.zip`, `7 715 472` bytes, SHA-256
  `4eec1e5728ac1b2e6962ade6179f4e3841ffb2095d6b7e227fb241ccd381b5c6`.
- Public PKG: `GRAF-2026.08.28.11.pkg`, `7 526 525` bytes, SHA-256
  `d996c928e5419c346cee66983ee878d5c8bc7a0a54cd6fc381739616e7186e9c`.
- Public appcast: `graf-appcast.xml`, `4 739` bytes, SHA-256
  `6e7336629f4c4323136e78a1b08e73ce84d6d352b3e51d874a9689e984ad7291`;
  enclosure version `2026.08.28.11`, length `7715472`.
- Fresh public download повторно прошёл SHA-256, ZIP integrity,
  `validate-app-updates.sh`, codesign, stapler, package signature и `spctl`.

Versioned ZIP/PKG/checksums и `graf.pkg` были опубликованы до appcast под единым
deploy lock. Предыдущие live aliases сохранены:

- `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf.pkg.pre-v2026.08.28.11-20260828T172702Z`;
- `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.08.28.11-20260828T172702Z`.

## Installed-app billing smoke

- `/Applications/GRAF.app` штатно обновлён Sparkle с `2026.08.28.8` до
  `2026.08.28.11`; установленный bundle прошёл codesign, stapler и `spctl`.
- `/billing` открылся внутри GRAF: активная подписка, существующий платёж
  `INV-41CF58F0C2114670948F` со статусом «Оплачен», чек зарегистрирован.
- `/billing/checkout` показал тарифы `1 000 ₽/месяц` и `10 000 ₽/год`.
- Promo preview для `P4_GRAF` прошёл desktop POST route и ожидаемо вернул
  `promo_invalid`, потому что этот одноразовый код уже использован текущим
  пользователем.
- Checkout start прошёл desktop POST route и вернул `already_active`: тариф уже
  активен, повторная оплата не создана.
- Экран «Функция недоступна» не появился ни на одном billing action. Новый
  платёж не создавался.

## Ограничения

- YooKassa остаётся только в test-shop; production-магазин не включался.
- CodeRabbit не завершил review из-за внешнего лимита и не считается PASS.
- После выпуска изменяется только docs-only closeout metadata; release tag и
  production runtime остаются на immutable SHA выше.

## Связи

- Desktop billing fix: https://github.com/yshishenya/graf/pull/5924
- Release preparation: https://github.com/yshishenya/graf/pull/5925
- Healthcheck budget: https://github.com/yshishenya/graf/pull/5931
- Deploy lock bootstrap: https://github.com/yshishenya/graf/pull/5935
- Server release gate: https://github.com/yshishenya/graf/issues/5929
- Desktop release gate: https://github.com/yshishenya/graf/issues/5923
