# Production receipt — v2026.08.15.1

Дата: 2026-08-15

## Результат

- Серверный runtime: commit `63cdbcc57653c8d112f901fa6d41f2d135c9d6c3`;
  health, migrations, backup/restore rehearsal и production smoke — успешно.
- macOS release tag: `v2026.08.15.1` на commit
  `9568d747a0141369ece4c8ba42606599be724852`.
- GitHub Release опубликован:
  https://github.com/yshishenya/crisp/releases/tag/v2026.08.15.1

## Публичные артефакты

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- ZIP: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.15.1.zip
- PKG: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.15.1.pkg
- `graf.pkg` синхронизирован с тем же notarized PKG в commit `1f6f263d`.
- ZIP SHA-256: `360ac8170de3336853ee0f213e284b283372c8982a094f286967dd81d5a0a6c9`.
- PKG SHA-256: `7fef6aa04b913fc3352a23417148b5bc0211ba9e64f90a97b0c78f1ba416e772`.
- Appcast SHA-256: `4dbf4e7ca1e9a74c681d23f94e277531b9650340b9623f9d83e8d7cf0394732b`.

## Проверка и совместимость

- Sparkle archive/appcast validation с предыдущей `2026.08.13.4` — pass.
- Apple notarization для ZIP и PKG — `Accepted`; stapler и Gatekeeper — pass.
- Обновление добавляет бесшовный desktop-to-browser handoff для billing;
  сам billing остаётся browser-owned.
- Откат: восстановить сохранённый предыдущий appcast и оставить предыдущий ZIP;
  новые артефакты не удалять до завершения наблюдения.
