# Release receipt: v2026.08.19.2

## Сводка

- Release tag: `v2026.08.19.2`
- Deployed SHA: `71ed831e9d6f2661a88e8708ec0d408ffbe8bd8f`
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
| macOS Swift tests | pass; 696 тестов |
| Server PostgreSQL suite | pass; 3049 passed / 1 skipped |
| Strict RLS suite | pass; 42 passed / 1 skipped |
| Server lint и Python compile | pass |
| Production Compose config | pass |
| Deployment evidence scan | pass |
| Disposable cleanup | pass |

После gate код или release-конфигурация exact SHA не менялись. Этот
metadata-only closeout не требует повторного полного CI.

## Production deployment

- Dry-run: `pass`.
- Execute: `pass`; runtime SHA совпадает с release SHA.
- Backup и restore rehearsal: `pass`.
- Backup evidence ID: `20260819T162909Z`.
- Миграции, database identity и RLS boundary: `pass`.
- API health/readiness, Temporal, processing worker и media worker: `pass`.
- Production smoke, automatic dispatch gate и cleanup: `pass`.
- Guarded rollback: не потребовался.

## Public macOS release

- Developer ID Application / Installer, universal binary `x86_64 arm64`,
  notarization, stapling и Gatekeeper: `pass`.
- Team ID: `94N8HYG672`.
- Apple ZIP request: `ab4f8597-96c3-4964-8819-ade1e3e879e4` (`Accepted`).
- Apple PKG request: `fa3ae06a-98b5-4442-9dc8-19091c0c6b42` (`Accepted`).
- Sparkle continuity `Developer ID → Developer ID`: `pass`; предыдущая версия
  `2026.08.19.1`, trust generation `1`, Keychain custody `ready`.
- ZIP: `c02c1bbcf1786bd20192c20c9852c1ab9e222613f4f3c3c4b2e4bf72be620900`,
  `6528048` bytes.
- PKG: `e8666adfd68d8a745db215317303e95afca19960d1a73a78b32fd2e6b59eeae9`,
  `6334718` bytes.
- Appcast: `c2fd838c457f2f89804d4b05db550c453f4946d5245104218501a8ced1516630`,
  `4768` bytes; enclosure `6528048` bytes.
- Предыдущий appcast сохранён; backup evidence ID:
  `graf-appcast.xml.pre-v2026.08.19.2-20260819T164057Z`.
- Versioned ZIP, PKG и checksum-файлы опубликованы и проверены по HTTPS до
  замены appcast; appcast заменён последним.
- Повторный HTTPS readback, XML, archive integrity, Ed25519,
  `validate-app-updates.sh`, stapler и Gatekeeper: `pass`.

## Установленные приложения и визуальный smoke

- `/Applications/GRAF.app` штатно обновлён Sparkle с `2026.08.19.1` до
  `2026.08.19.2` и перезапущен.
- Production bundle ID и Team сохранены: `pro.2brain.graf`, `94N8HYG672`.
- Permission retention: `pass`; нового системного prompt не было, приложение
  показало «Микрофон и системный звук готовы».
- После relaunch прежняя web-сессия показала login с `missing_auth_context`.
  Это не подтверждено как регрессия обновления: до обновления срок действия
  загруженной сессии отдельно не фиксировался.
- `/Applications/GRAF Dev.app` установлен отдельно; bundle ID
  `pro.2brain.graf.dev`, configured origin `127.0.0.1:8081`, стабильная
  designated requirement, production updater отсутствует.
- Установленный `GRAF Dev` проверен через macOS UI в безопасном offline-state:
  native-toggle находится сверху, повторный клик сворачивает панель в той же
  позиции, перекрытий нет, статусы и accessibility labels корректны.
- Реальный capture не запускался.

## Release и rollback

- GitHub Release опубликован как latest:
  <https://github.com/yshishenya/crisp/releases/tag/v2026.08.19.2>.
- Release содержит русские notes, ZIP, PKG, appcast, checksums и metadata-only
  signing attestation.
- Откат не потребовался. Для recovery сохранены previous signed appcast,
  [предыдущий versioned archive](../../releases/v2026.08.19.1.md) и production
  backup. Sparkle downgrade ниже текущей версии не публикуется; при
  необходимости используется guarded forward-fix с большим CalVer.

## Ограничения

- Миграции пользовательских данных не выполнялись и не требуются.
- Генерация итогов не менялась этим release train; принятые итоги не заменяются
  автоматически.
- Clean-Mac first-grant не повторялся; проверено сохранение уже выданных
  разрешений при штатном update.
- Реальный capture не запускался, чтобы не создавать пользовательское аудио.
- Public-link readback остаётся выключен действующей политикой безопасности.

## Связи

- PR: #5385, #5386.
- Issues: #5372–#5384.
- Spec Kit: `174` с продолжением ранее закрытых sidebar-срезов `172` и `173`.
