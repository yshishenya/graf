# Production closeout: `v2026.08.23.9`

## Immutable release

- Tag and GitHub Release: `v2026.08.23.9` — https://github.com/yshishenya/graf/releases/tag/v2026.08.23.9
- Release SHA: `34d0b4b2edcd510b3fdf09c76e5edf9ac329c4bc`
- Runtime branch/SHA: `master` / `34d0b4b2edcd510b3fdf09c76e5edf9ac329c4bc`
- Implementation PR: https://github.com/yshishenya/graf/pull/5621
- Feature: `specs/193-automatic-recording-reliability/`
- Validation lane: `release-deploy`
- Дата выкладки и closeout: 2026-08-23

Receipt содержит только агрегированные технические метаданные. Секреты,
учётные данные, signed URLs, аудио, расшифровки и содержимое встреч не
включались.

## Validation and deployment

| Гейт | Результат |
| --- | --- |
| Feature-focused macOS reliability suite | PASS; 135/135 тестов |
| Full local CI exact-SHA | Не запускался по прямому указанию владельца; PASS не заявляется |
| Branch/tag/runtime synchronization | PASS; `master`, tag и runtime на одном SHA |
| Production deployment | PASS; execute с явно согласованным `--skip-local-ci` |
| Backup and restore rehearsal | PASS |
| Migration/RLS/runtime readiness | PASS; migration head `0077_provider_unlink_xworkspace` |
| API, workers and Temporal | PASS; runtime containers healthy |
| Production synthetic smoke and cleanup | PASS; без приватных материалов |
| Public health | PASS; `/api/v1/health/live` и `/api/v1/health/ready` вернули HTTP 200 |
| Rollback | Не потребовался; предыдущий подписанный appcast сохранён |

Full CI остаётся отдельным открытым ограничением и не подменяется focused
тестами или smoke.

## Public macOS release

- Developer ID Application/Installer, universal binary, Apple notarization,
  stapling и Gatekeeper: PASS.
- Sparkle Developer ID → Developer ID continuity с `2026.08.23.6`: PASS.
- `validate-app-updates.sh` с публичными ZIP/appcast и предыдущим `.6`: PASS.
- Публичный feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- ZIP: `GRAF-2026.08.23.9.zip`, 7,634,369 bytes,
  SHA-256 `0b877040564aeef99fafa980bb8bd08bab20943f1b99cf8bd5d299742e0c1713`.
- PKG: `GRAF-2026.08.23.9.pkg`, 7,443,289 bytes,
  SHA-256 `774d47dee738ed16e222ed377785cbd372ca988f013514b27e7434ecb3944cd8`.
- Appcast SHA-256:
  `277449671973ab13ec4f0a1c0ddb61b056d7dca26dc44f5fbb7f63981c523c34`;
  enclosure length `7634369` bytes.
- Предыдущий appcast сохранён на production host:
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.08.23.9-20260823T114901Z`.
- Fresh HTTPS readback совпал с локальными ZIP, PKG, appcast и checksums;
  appcast и archive повторно прошли Ed25519 verification.

## Installed-client update

- До публикации installed `/Applications/GRAF.app` был `2026.08.23.6`.
- В metadata-only журнале GRAF зафиксированы: manual check, offer `.9`,
  `user_choice_install`, download start/finish, install request и безопасная
  задержка на время protected work.
- После relaunch приложение запустилось на `2026.08.23.9`; `.pkg` вручную не
  устанавливался.
- Bundle ID `pro.2brain.graf`, Team `94N8HYG672`, feed URL и Sparkle public
  key сохранились; installed app прошёл stapler validation и Gatekeeper.
- После relaunch permission readiness осталась `microphone=granted`,
  `systemAudio=granted`, `ready=true`; observer перешёл в live generation.

## Scope and limitations

- Feature 193 меняет только надёжность автоматической записи: независимые
  AudioHAL/Sensor Indicator источники, bounded trigger retry, повторные
  authorization/readiness checks, observer recovery и deterministic cookie
  reconciliation. API и схема данных Feature 193 не менялись.
- Реальные встречи, аудио и расшифровки в smoke не использовались.
- Для уже обновившихся клиентов откат выполняется только новым релизом с
  большим CalVer; unsigned или lower-version Sparkle downgrade запрещён.
