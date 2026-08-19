# Release receipt: v2026.08.19.1

## Сводка

- Release tag: `v2026.08.19.1`
- Deployed SHA: `3ebb8d450feeb6dc49656e57534f02bf3f2e1ac8`
- Ветка проверки: `master`
- Validation lane: `release-deploy`
- Exact-SHA gate: `pass`
- Production execute: `pass`
- Public macOS release: `pass`
- Дата проверки и выкладки: `2026-08-19`

Receipt содержит только агрегированные результаты. Credentials, signed URLs,
сырые логи, аудио, тексты встреч и приватные скриншоты не сохранены.

## Exact-SHA full gate

Authoritative gate выполнен внутри approved
`infra/scripts/cd-remote.sh --execute --branch master`.

| Этап | Результат |
| --- | --- |
| macOS Swift tests | pass; 695 тестов |
| Server PostgreSQL suite | pass; 3049 passed / 1 skipped |
| Strict RLS suite | pass; 42 passed / 1 skipped |
| Server lint и Python compile | pass |
| Production Compose config | pass |
| Deployment evidence scan | pass |
| Disposable cleanup | pass |

После gate код или release-конфигурация exact SHA не менялись. Финальный
metadata-only closeout не требует повторного полного CI.

## Production deployment

- Dry-run: `pass`.
- Execute: `pass`; runtime SHA совпадает с release SHA.
- Backup и restore rehearsal: `pass`.
- Backup: `/opt/projects/2brain-rec/backups/20260819T121645Z`.
- Миграции, database identity и RLS boundary: `pass`.
- API health/readiness, Temporal, processing worker и media worker: `pass`.
- Production smoke и automatic dispatch gate: `pass`.
- Guarded rollback: не потребовался.

## Public macOS release

- Developer ID Application / Installer, universal binary, notarization,
  stapling и Gatekeeper: `pass`.
- Apple ZIP request: `d26ade70-ebc9-4bd6-9b40-a07551dbad34`.
- Apple PKG request: `b3937245-45e1-4e1a-a8f0-cafeb2334e72`.
- Sparkle continuity `Developer ID → Developer ID`: `pass`; предыдущая версия
  `2026.08.18.2`, trust generation `1`, Keychain custody `ready`.
- ZIP: `670de40caab28894f730cb49de71e6c2c0df6a7a760126124edb5fb659c950cd`,
  `6528915` bytes.
- PKG: `16dc373871d51ac79d883bb8237c808e35d005f6a0e6d4ba375aa6eca5cec213`,
  `6337916` bytes.
- Appcast: `3191308dd304728d9dd070f75816c4b81b304910d66df07198ade64116270d12`,
  enclosure `6528915` bytes.
- Предыдущий appcast сохранён как
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.08.19.1-20260819T123219Z`.
- Versioned ZIP, PKG и checksum-файлы опубликованы и проверены по HTTPS до
  замены appcast; appcast заменён последним.
- Повторный HTTPS readback, XML, archive integrity, Ed25519, stapler и
  Gatekeeper: `pass`.

## Установленные приложения и визуальный smoke

- `/Applications/GRAF.app` штатно обновлён Sparkle до `2026.08.19.1` и
  перезапущен.
- Production bundle ID и Team сохранены: `pro.2brain.graf`, `94N8HYG672`.
- Permission retention: `pass`; нового системного prompt не было, приложение
  показало «Микрофон и системный звук готовы» и `Готово к записи`.
- Native-toggle остаётся в верхнем правом слоте и раскрывается/сворачивается
  повторным кликом в одной позиции.
- Web sidebar на широком окне открыт по умолчанию; compact/expanded toggle,
  профиль, поиск и нижний playback не перекрываются.
- Настройки используют одну левую навигацию без пустой legacy-колонки.
- `/Applications/GRAF Dev.app` атомарно обновлён из release-кода; bundle ID
  `pro.2brain.graf.dev`, loopback `127.0.0.1:8081`, отдельная стабильная
  designated requirement, production updater отсутствует.
- Во встроенном браузере production login проверен на обычной и узкой ширине:
  horizontal overflow `0`, console errors `0`, download CTA присутствует,
  отдельной кнопки регистрации нет.

## Release и rollback

- GitHub Release опубликован как latest:
  <https://github.com/yshishenya/crisp/releases/tag/v2026.08.19.1>.
- Release содержит русские notes, ZIP, PKG, appcast, checksums и metadata-only
  signing attestation.
- Откат не потребовался. Для recovery сохранены previous signed appcast,
  предыдущий versioned archive и production backup. Sparkle downgrade ниже
  текущей версии не публикуется; при необходимости используется guarded
  forward-fix с большим CalVer.

## Ограничения

- Clean-Mac first-grant не повторялся; проверено сохранение уже выданных
  разрешений при штатном update.
- Реальный capture не запускался, чтобы не создавать пользовательское аудио.
- Генерация итогов не менялась этим release train.
- Public-link readback остаётся выключен действующей политикой безопасности.

## Связи

- PR: #5363, #5371.
- Issues: #5333–#5339, #5364–#5370.
- Spec Kit: `161`, `168`, `169`, `170`, `171`, `172`, `173`.
