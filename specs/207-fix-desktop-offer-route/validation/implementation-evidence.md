# Feature 207: production release evidence

Дата closeout: 2026-08-28.

## Immutable release

- Release: `v2026.08.28.8`.
- Release, tag, deployed runtime и проверенный `origin/master` указывали на
  `cdb0464c43e5c76bded8d660943001f186a0de6d` в момент публикации.
- Implementation PR: #5905; RLS release blocker: #5914; release metadata: #5915.
- Validation lane: release/deploy.

## Validation and deployment

- Focused offer-route suite: PASS; exact `/offer` разрешён, неизвестные sibling
  routes и trailing-slash variants остаются fail-closed.
- Fast CI: PASS; `1249 passed`, Ruff и compile PASS.
- Full exact-SHA CI: PASS; macOS `767/767`, server `3485 passed, 1 skipped`,
  strict RLS `52 passed, 1 skipped`; performance, lint, compile, Compose и
  deployment evidence checks — PASS.
- Production deploy: PASS; backup/restore rehearsal, migrations, health,
  synthetic smoke и cleanup выполнены штатным pipeline.
- CodeRabbit не выполнил новый review из-за исчерпанной квоты; это не считается
  PASS данного внешнего гейта.

## Public macOS release

- Developer ID Application и Developer ID Installer: PASS.
- Apple notarization: ZIP `b2ff4c2c-90fa-4509-9442-34f514c7e6e9` — Accepted;
  PKG `eee1cc99-da18-4c87-ac92-d7bd4f2218e9` — Accepted.
- Stapler и Gatekeeper для app/PKG: PASS.
- Локальный Keychain Sparkle signer и Developer ID continuity
  `2026.08.24.8 → 2026.08.28.8`: PASS.
- Публичные ZIP, PKG, checksum и appcast скачаны повторно; SHA-256, ZIP integrity,
  PKG notarization и appcast enclosure `7713165` bytes: PASS.
- GitHub Release опубликован: https://github.com/yshishenya/graf/releases/tag/v2026.08.28.8

## Installed production smoke

- Штатный Sparkle flow предложил `2026.08.28.8` установленному
  `2026.08.24.8`, скачал обновление и успешно перезапустил GRAF.
- `/Applications/GRAF.app` имеет `CFBundleVersion` и
  `CFBundleShortVersionString` `2026.08.28.8`; codesign, stapler и Gatekeeper —
  PASS как notarized Developer ID.
- Реальный путь `Тариф и оплата → Выбрать тариф → оферту` открыл публичную
  страницу «Условия оплаты и возврата ГРАФ» во внешнем браузере Zen.
- После клика GRAF остался на `/billing/checkout`; экран «Функция недоступна» не
  появился. Новый платёж не создавался.

## Scope

- Production YooKassa остаётся в режиме test shop; production shop не включался.
- Evidence содержит только безопасные технические метаданные, без credentials,
  provider identifiers, полных контактных данных и содержимого встреч.
