# Production closeout: `v2026.08.23.11`

## Immutable release

- Tag and GitHub Release: [`v2026.08.23.11`](https://github.com/yshishenya/graf/releases/tag/v2026.08.23.11)
- Release SHA: `3aa338683279d4ab602fbbcd2728552996355a31`
- Runtime branch/SHA: `master` / `3aa338683279d4ab602fbbcd2728552996355a31`
- Implementation PR: https://github.com/yshishenya/graf/pull/5638
- Feature: `specs/197-recording-indicator-polish/`
- Validation lane: `release-deploy`
- Дата выкладки и closeout: 2026-08-23

Receipt содержит только агрегированные технические метаданные. Секреты,
учётные данные, signed URLs, аудио, расшифровки и содержимое встреч не
включались.

## Exact-SHA validation and deployment

| Гейт | Результат |
| --- | --- |
| Focused macOS source-indicator tests | PASS; `CaptureIndicatorTests` 13/13 и `AppControlAccessibilityTests` 22/22 |
| Full Swift suite macOS | PASS; `753/753`; `ContractValidation: PASS` |
| Server CI | Не запускался по явному указанию владельца релиза: Feature 197 не меняет `apps/server`, `infra` или серверные контракты. Это не считается успешным полным CI. |
| Branch/tag synchronization | PASS; `origin/master`, tag и merge commit указывают на `3aa338683279d4ab602fbbcd2728552996355a31` |
| Production CD | PASS; execute на exact SHA с согласованным `--skip-local-ci` |
| Backup и restore rehearsal | PASS; backup `/opt/projects/2brain-rec/backups/20260823T164425Z` |
| Migrations и runtime readiness | PASS |
| Production synthetic smoke и cleanup | PASS; без приватных материалов |
| Public health | PASS; `/api/v1/health/live` вернул `{"status":"ok"}`, `/api/v1/health/ready` — `{"status":"ready"}` |
| Remote checkout readback | PASS; `master` и production runtime на release SHA, staging очищен |
| Rollback | Не потребовался; предыдущие подписанные appcast и installer сохранены |

Поскольку server CI был явно пропущен, этот receipt не заявляет full-CI pass.
Остальные production gates CD, включая backup/restore, migrations, readiness,
smoke и health, прошли.

## Public macOS release

- App notarization: `39e03892-f597-4a06-b4ee-42b9908335fc` — `Accepted`.
- PKG notarization: `4b292e50-9531-48f5-99d2-bc9fc134c1fa` — `Accepted`.
- Developer ID Application/Installer, stapler и Gatekeeper: PASS.
- Sparkle signing custody: local Keychain signer, trust generation `1`, custody
  attestation опубликована вместе с релизом.
- `validate-app-updates.sh`: PASS; Developer ID → Developer ID, continuity
  `in-app`, `2026.08.23.10 → 2026.08.23.11`.
- Публичный HTTPS fetch подтвердил SHA-256, XML, ZIP integrity, PKG signature,
  notarization, Gatekeeper и Sparkle enclosure signature.
- ZIP: `GRAF-2026.08.23.11.zip`, 7,648,783 bytes,
  SHA-256 `00b18cb23c2c1ff0cdebe8ac8d29a0927fe0ee5e5aadc52aba1a036d90cc2290`.
- PKG: `GRAF-2026.08.23.11.pkg`, SHA-256
  `c61ca7e88c407904977a88e0d1581929492c0e0adb1e9bb8f77df4a2ce8c0bbb`.
- Public installer `graf.pkg`: 7,457,364 bytes, тот же SHA-256, что и versioned PKG.
- Публичный appcast: `graf-appcast.xml`, 3,818 bytes, SHA-256
  `bcff13dc9e0b740ea6c59633822ea906e4779151b880bc7103784bdd9539b521`;
  enclosure length `7648783` bytes.
- GitHub Release опубликован, `isDraft=false`; ZIP, PKG, checksums, appcast,
  notes и signing attestation доступны в опубликованном релизе.

Предыдущие live files сохранены на production host до замены алиасов:

- `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf.pkg.pre-v2026.08.23.11-20260823T165809Z`
- `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.08.23.11-20260823T165809Z`

## Installed-client update

- До публикации `/Applications/GRAF.app` был `2026.08.23.10`.
- Штатная команда `GRAF → Check for Updates…` получила публичный feed и
  предложила `2026.08.23.11`.
- После Sparkle update и relaunch `/Applications/GRAF.app` имеет
  `CFBundleVersion` и `CFBundleShortVersionString` `2026.08.23.11`, bundle ID
  `pro.2brain.graf`.
- Installed app прошёл `codesign --verify --deep --strict`, stapler validation
  и Gatekeeper assessment как notarized Developer ID.

## Scope and limitations

- Feature 197 меняет только presentation persistent recording indicator:
  источник записи показывается внутри одной верхней капсулы, duplicate sidebar
  row удалён; capture path, server API, схема и разрешения не менялись.
- Проверка использовала безопасные synthetic metadata и локальный smoke; реальные
  встречи, аудио и расшифровки в evidence не записывались.
- Для уже обновившихся клиентов откат выполняется только новым релизом с большим
  CalVer; unsigned или lower-version Sparkle downgrade запрещён.
