# Production closeout: `v2026.08.23.10`

## Immutable release

- Tag and GitHub Release: [`v2026.08.23.10`](https://github.com/yshishenya/graf/releases/tag/v2026.08.23.10)
- Release SHA: `a8eb13e0016271078cb0b76dd9bc50661d7def53`
- Runtime branch/SHA: `master` / `a8eb13e0016271078cb0b76dd9bc50661d7def53`
- Implementation PR: https://github.com/yshishenya/graf/pull/5622
- Feature: `specs/194-global-auto-start-defaults/`
- Validation lane: `release-deploy`
- Дата выкладки и closeout: 2026-08-23

Receipt содержит только агрегированные технические метаданные. Секреты,
учётные данные, signed URLs, аудио, расшифровки и содержимое встреч не
включались.

## Exact-SHA validation and deployment

| Гейт | Результат |
| --- | --- |
| Full CI на exact release SHA | PASS; `3318 passed`, `1 skipped`; Swift `752/752` |
| Lint, Python compile, Compose, evidence и RLS gates | PASS |
| Branch/tag/runtime synchronization | PASS; `master`, tag и production runtime на одном SHA |
| CD dry-run | PASS; `infra/scripts/cd-remote.sh --dry-run --branch master` |
| CD execute | PASS; `--execute --branch master`, без `--skip-local-ci` |
| Backup и restore rehearsal | PASS |
| Migrations и runtime readiness | PASS; migration, API, workers и Temporal readiness прошли |
| Production synthetic smoke и cleanup | PASS; без приватных материалов |
| Public health | PASS; `/api/v1/health/live` вернул `{"status":"ok"}`, `/api/v1/health/ready` — `{"status":"ready"}` |
| Installed-client Sparkle update | PASS; `/Applications/GRAF.app` обновлён `.9 → .10`, перезапущен и прошёл подпись/notarization/Gatekeeper |
| Remote checkout readback | PASS; `master` на release SHA, рабочее дерево чистое |
| Rollback | Не потребовался; предыдущий подписанный appcast сохранён |

CD отдельно отметил `automatic_retry`, `backfill_inventory`, `range_playback`
и `normalization_cleanup` как `required_post_deploy`. Это maintenance
follow-ups, а не часть release smoke и не подменяются этим receipt.

## Public macOS release

- App notarization: `176a77e4-75eb-4908-a2dd-d1fe2e1d4f17` — `Accepted`.
- PKG notarization: `ea651dfd-961c-4d59-892e-2776ae1e3c49` — `Accepted`.
- Developer ID Application/Installer, stapler и Gatekeeper: PASS.
- Sparkle signing custody: keychain account `graf-release-signing`, trust
  generation `1`, custody `ready`.
- `validate-app-updates.sh`: PASS; Developer ID → Developer ID, continuity
  `in-app`.
- Публичные Ed25519-проверки appcast и ZIP: PASS.
- ZIP: `GRAF-2026.08.23.10.zip`, 7,651,763 bytes,
  SHA-256 `8148642883b835d0cf13ad3ac3b2e2fbdef9838d4af336a5db992372eabed594`.
- PKG: `GRAF-2026.08.23.10.pkg`, SHA-256
  `bdf9efd010789c01006e428bc72f9956dd21f6e72c22931da865388b3beb43c0`.
- Публичный appcast: `graf-appcast.xml`, SHA-256
  `f538fafeeb4578ec18e46f64b5d3e59b57e5eed833b3fc6a6e00fc916c6a54c9`,
  enclosure length `7651763` bytes.
- Public PKG повторно скачан: `pkgutil --check-signature`, stapler и
  `spctl --assess --type install` прошли.
- GitHub Release опубликован; временный `GRAF-2026.08.23.10-candidate.zip`
  удалён, финальные assets доступны в опубликованном релизе.

## Installed-client update

- Встроенная команда `Check for Updates…` получила публичный feed и показала
  `2026.08.23.10`; пользователь подтвердил установку через Sparkle.
- Metadata-only журнал зафиксировал `user_choice_install`,
  `download_finished`, `install_requested` и последующий `app_update.started`
  уже с `installedVersion=2026.08.23.10`.
- `/Applications/GRAF.app` сейчас имеет `CFBundleVersion` и
  `CFBundleShortVersionString` `2026.08.23.10`, bundle ID `pro.2brain.graf`;
  codesign, stapler и Gatekeeper прошли. Ручной PKG не использовался.

## Связи

- Release notes: [v2026.08.23.10](../../releases/v2026.08.23.10.md)
- Feature tasks: `specs/194-global-auto-start-defaults/tasks.md`
