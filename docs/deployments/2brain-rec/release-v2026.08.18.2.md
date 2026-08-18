# Release receipt: v2026.08.18.2

## Сводка

- Release tag: `v2026.08.18.2`
- Deployed SHA: `e6e838b5870de2b882890d5b306c477493dd9f2e`
- Ветка проверки: `master`
- Validation lane: `release-deploy`
- Результат exact-SHA gate: `pass`
- Результат production execute: `pass`
- Дата проверки и выкладки: `2026-08-18`

Этот receipt содержит только агрегированные результаты. Пароли, токены,
подписанные URL, сырые логи, аудио и содержимое встреч сюда не записываются.

## Exact-SHA full local gate

Команда: `RLS_TEST_DATABASE_URL=<loopback disposable URL> infra/scripts/ci-local.sh --full`

| Этап | Результат |
| --- | --- |
| macOS Swift tests | pass; 693 теста |
| ContractValidation | pass |
| Server PostgreSQL suite | pass; 3046 passed / 1 skipped |
| Strict RLS suite | pass; 42 passed / 1 skipped |
| Server lint | pass |
| Python compile | pass |
| RLS hardening validation | pass; direct SQL probes завершены |
| Production Compose config | pass |
| Deployment evidence scan | pass; 28 файлов |
| Disposable cleanup | pass; database=0, role=0 |

Проверка выполнялась на отдельном loopback PostgreSQL-контейнере с базой,
ограниченной именем disposable RLS scratch database. После завершения база,
временная probe role и контейнер удалены.

## Production deployment

Dry-run: `infra/scripts/cd-remote.sh --dry-run --branch master` — `deploy_result=dry_run`.

Execute: `infra/scripts/cd-remote.sh --execute --branch master` — `deploy_result=pass`.

Production execute подтвердил:

- backup и restore rehearsal — pass;
- миграция до `0073_account_auth_linking`, database identity и RLS boundary — pass;
- health/readiness, Temporal, processing и media worker — pass;
- production smoke и automatic dispatch gate — pass;
- публичная landing-загрузка и текущий update archive — pass;
- guarded rollback — не потребовался.

Backup: `/opt/projects/2brain-rec/backups/20260818T210036Z`.

План dry-run подтвердил branch sync, pinned SHA, обязательный полный local CI,
backup, restore rehearsal, runtime secret checks, migration/RLS boundary,
readiness, production smoke, rollback и post-deploy maintenance checks.
Remote state до execute не изменялся.

## Public macOS release

- Developer ID Application / Installer, notarization, stapler и Gatekeeper — pass;
  Apple ZIP request `0e54b4c1-3b56-411a-890a-5397a81eacf1`, PKG request
  `08b5779b-6996-4316-9e96-12c48c67461f`.
- Sparkle continuity `Developer ID → Developer ID` — pass; trust generation `1`.
- ZIP: `https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.18.2.zip`;
  SHA-256 `e2292410b442a1d3e1bcfeb49a96492ade64b59984d0aa068be58964769abaf7`.
- PKG: `https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.18.2.pkg`;
  SHA-256 `0a6e0da127845eb3161e885f1a254d0f4cea782785031dd6be5c26b3f0a16c74`.
- Appcast: `https://rec.2brain.pro/static/public/downloads/graf-appcast.xml`;
  SHA-256 `e33be6a8d257e0aa68465a83598d04d69e95eea860451d6fa0406907c49af674`.
- Предыдущий appcast сохранён как
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.08.18.2-20260818T210825Z`.
- Повторный HTTPS readback ZIP/PKG/appcast, длина enclosure, XML, ZIP integrity,
  Sparkle update validation, notarization и Gatekeeper — pass.

## Release and rollback status

- GitHub Release опубликован и содержит русский changelog,
  ZIP, PKG, checksums, appcast и metadata-only signing attestation.
- Rollback не потребовался. Для recovery сохранены предыдущий релиз
  `v2026.08.18.1`, versioned archive и backup appcast; откат выполняется только
  guarded CD-процедурой.
- `automatic_retry_result`, `backfill_inventory_result`, `range_playback_result`
  и `normalization_cleanup_result` отмечены как `required_post_deploy`; это
  отдельные maintenance follow-ups и не являются частью smoke acceptance.
- Генерация итогов в production этим release train не включалась; текущий
  принятый результат не заменяется автоматически.

## Связи

- Spec: `specs/167-rls-ci-runtime/spec.md`
- Plan: `specs/167-rls-ci-runtime/plan.md`
- Tasks: `specs/167-rls-ci-runtime/tasks.md`
- PR: #5325
- GitHub issues: #5316–#5324
