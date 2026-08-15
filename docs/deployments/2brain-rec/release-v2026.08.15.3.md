# Production receipt — v2026.08.15.3

Дата: 2026-08-15

## Результат

- PR #5122 влит в `master`.
- Runtime выкачен на commit `514ae95b32781d5d42addaeb7bda9f38d9d8cea8`.
- Production CD завершён с `--skip-local-ci` по явному разрешению владельца;
  ранее зафиксированный полный CI не повторялся.
- Health live/ready: HTTP 200.
- Root и `/download`: HTTP 200.
- Неаутентифицированный `/billing`: безопасный redirect на
  `/login?next=%2Fbilling&error=missing_auth_context`; legacy header error не
  возвращается.

## Публичные артефакты

- Appcast: `https://rec.2brain.pro/static/public/downloads/graf-appcast.xml`
- ZIP: `https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.15.3.zip`
- PKG: `https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.15.3.pkg`
- Канонический `/download` package (`graf.pkg`) совпадает с PKG `.3`.
- ZIP SHA-256: `47bf3c21f8370bd67c9ebd7c91a8e8c3bed3256e028e6b721232db43d0996094`.
- PKG SHA-256: `c4a36a0731d1d14b4d13b8faca0a55a638c2c3349bdd90aa73db4440e027a5d7`.
- Appcast SHA-256: `32c8b8c2099d7cd52e431f06c7227a9a1098bc9638bb1ff89fd7c54c9665643a`.

## Исправление подписи обновления

- После первой публикации обнаружено, что ZIP имел тот же размер, но не те же
  байты, для которых был подписан appcast.
- ZIP заменён на подписанный staging-артефакт:
  `a809c144e268dc1de96f0a1a9fcecac13c34d78e26f76d81aa2323b7d7eefbc6`.
- Публичный ZIP повторно скачан, `sign_update --verify` и полная
  `validate-app-updates.sh` проверка с live appcast прошли.
- Предыдущий ошибочный ZIP сохранён в backup как
  `GRAF-2026.08.15.3.zip.invalid-signature`.

## Проверка и откат

- Apple notarization ZIP/PKG: `Accepted`; stapler и Gatekeeper: PASS.
- Sparkle archive/appcast validation и подпись Keychain: PASS.
- Публичный appcast указывает на `.3` ZIP, HTTPS и точную длину 6,451,507 байт;
  повторная загрузка и XML-проверка прошли.
- Recoverable backup старых `.1` артефактов сохранён в
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/.release-v2026.08.15.3`.
- Для отката восстановить backup appcast/артефакты и вернуть runtime на
  предыдущий commit штатным `cd-remote.sh` rollback-процессом.
