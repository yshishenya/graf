# Production receipt: v2026.08.13.3 macOS Sparkle update

Дата: 2026-08-13  
Контур: `https://rec.2brain.pro`  
Release tag: `v2026.08.13.3`  
Release commit: `a53965c72f3d175b740d91702b3b1916932986c7`

## Что опубликовано

- Sparkle appcast теперь сообщает `2026.08.13.3`.
- Публичный ZIP содержит universal `GRAF.app` для `arm64` и `x86_64`.
- Публичный PKG содержит тот же notarized Developer ID app bundle.
- Предыдущий appcast сохранён для отката:
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.08.13.3-20260813T161301Z`.

Публикация Sparkle-артефактов выполнена вместе с guarded server rollout:
production runtime закреплён на SHA `a53965c72f3d175b740d91702b3b1916932986c7`,
том же SHA, что и release tag.

## Артефакты

| Артефакт | Размер | SHA-256 |
| --- | ---: | --- |
| `GRAF-2026.08.13.3.zip` | 6 434 703 | `194f488d42293791065876b69adab63fcf131e70feb72848f2ba99132993ba12` |
| `GRAF-2026.08.13.3.pkg` | 6 241 467 | `55ab33e64a7217b221a62be01fd3bc970704ef4f14891e936384aa99bbd61e49` |
| `graf-appcast.xml` | 2 560 | `7b271087973bc9992abee823323efb3589dfddfaaaabdddeec20426ff5dbec1b` |

Apple notarization:

- ZIP: `a8dbebb4-957d-4b7b-8558-4b329e9f0ebd` — Accepted.
- PKG: `24f48704-8f7c-4078-8c29-34a4917e09aa` — Accepted.
- Stapler validation и Gatekeeper для app/PKG — PASS.
- Developer ID Application/Installer и Sparkle keychain recovery signer — PASS.

## Финальная проверка

- Переход с `2026.08.07.2` прошёл `validate-app-updates.sh` с сохранением
  bundle identity, feed URL, public key и designated requirement.
- ZIP integrity и Sparkle archive/feed signatures — PASS.
- Live `/static/public/downloads/graf-appcast.xml` — HTTP 200, версия
  `2026.08.13.3`, enclosure URL и длина совпадают.
- Live ZIP и PKG — HTTP 200; SHA-256 и размеры совпадают с локальными
  артефактами.
- `/api/v1/health/live` и `/api/v1/health/ready` — HTTP 200; API, processing и
  media worker, Temporal, PostgreSQL и MinIO работают в healthy-состоянии.
- Публичные versioned assets были перемещены до атомарной замены appcast.
- Smoke не оставил временный staging-каталог.

В случае неуспешной проверки guarded deploy автоматически возвращает runtime и
публичный installer к предыдущему состоянию; предыдущий appcast сохранён по
пути выше.

GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.08.13.3

Receipt содержит только технические метаданные и не содержит пользовательских
данных, содержимого встреч, секретов или приватных ключей.

## Ограничения

- Отдельный физический smoke на Intel Mac остаётся ручным follow-up.
- Автоматическое обновление Sparkle не включается: пользователь подтверждает
  установку обновления.
- Checkout YooKassa остаётся выключенным (`TWOBRAIN_BILLING_CHECKOUT_ENABLED=false`).
